"""
Chaos / DR testing — prove failover works before production does.

State: User/chaos.json (active injects + last report).
During inject, router skips the target provider as if unavailable.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from tollgate.filelock import FileLock
from tollgate.paths import user_dir

_LOCK = threading.RLock()
CHAOS_NAME = "chaos.json"


def chaos_path(root: Path | None = None) -> Path:
    return (user_dir(root) / CHAOS_NAME).resolve()


def _empty() -> dict[str, Any]:
    return {"version": 1, "active": [], "last_report": None, "history": []}


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return _empty()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return _empty()
        raw.setdefault("active", [])
        raw.setdefault("history", [])
        return raw
    except Exception:  # noqa: BLE001
        return _empty()


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = time.time()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _purge_expired(data: dict[str, Any]) -> dict[str, Any]:
    now = time.time()
    active = []
    for row in data.get("active") or []:
        if not isinstance(row, dict):
            continue
        until = float(row.get("until") or 0)
        if until <= 0 or until > now:
            active.append(row)
    data["active"] = active
    return data


def status(*, root: Path | None = None) -> dict[str, Any]:
    path = chaos_path(root)
    with _LOCK:
        with FileLock(path):
            data = _purge_expired(_load(path))
            _write(path, data)
            return {
                "ok": True,
                "active": list(data.get("active") or []),
                "last_report": data.get("last_report"),
                "path": str(path),
            }


def is_provider_in_chaos(provider: str, *, root: Path | None = None) -> bool:
    pid = (provider or "").strip().lower()
    if not pid:
        return False
    st = status(root=root)
    now = time.time()
    for row in st.get("active") or []:
        if str(row.get("provider") or "").lower() != pid:
            continue
        until = float(row.get("until") or 0)
        if until <= 0 or until > now:
            return True
    return False


def start_chaos(
    provider: str,
    *,
    duration_s: float = 300.0,
    reason: str = "manual",
    root: Path | None = None,
) -> dict[str, Any]:
    pid = (provider or "").strip().lower()
    if not pid:
        return {"ok": False, "error": "provider required"}
    dur = max(1.0, float(duration_s or 300))
    path = chaos_path(root)
    with _LOCK:
        with FileLock(path):
            data = _purge_expired(_load(path))
            # replace existing inject for same provider
            data["active"] = [
                r
                for r in (data.get("active") or [])
                if str(r.get("provider") or "").lower() != pid
            ]
            row = {
                "id": uuid.uuid4().hex[:12],
                "provider": pid,
                "started_at": time.time(),
                "until": time.time() + dur,
                "duration_s": dur,
                "reason": (reason or "manual")[:64],
            }
            data["active"].append(row)
            _write(path, data)
            return {"ok": True, "inject": row, "path": str(path)}


def stop_chaos(
    provider: str = "",
    *,
    all_injects: bool = False,
    root: Path | None = None,
) -> dict[str, Any]:
    path = chaos_path(root)
    with _LOCK:
        with FileLock(path):
            data = _purge_expired(_load(path))
            before = list(data.get("active") or [])
            if all_injects or not (provider or "").strip():
                data["active"] = []
            else:
                pid = provider.strip().lower()
                data["active"] = [
                    r
                    for r in before
                    if str(r.get("provider") or "").lower() != pid
                ]
            _write(path, data)
            return {
                "ok": True,
                "stopped": len(before) - len(data["active"]),
                "active": data["active"],
            }


def run_failover_test(
    provider: str,
    *,
    intent: str = "free_llm",
    requests: int = 5,
    duration_s: float = 60.0,
    live_chat: bool = False,
    root: Path | None = None,
) -> dict[str, Any]:
    """
    Inject chaos on ``provider``, fire N route (and optional chat) probes,
    clear inject, write report.

    Proves: traffic still routes when primary is down.
    """
    from tollgate import get_keys_service
    from tollgate.paths import pin_data_home_env

    pin_data_home_env()
    pid = (provider or "").strip().lower()
    if not pid:
        return {"ok": False, "error": "provider required"}
    n = max(1, min(100, int(requests or 5)))
    started = time.time()
    inj = start_chaos(pid, duration_s=duration_s, reason="failover_test", root=root)
    if not inj.get("ok"):
        return inj

    ks = get_keys_service()
    ok_n = 0
    fail_n = 0
    failover_n = 0
    used_providers: dict[str, int] = {}
    latencies: list[float] = []
    samples: list[dict[str, Any]] = []

    try:
        for i in range(n):
            t0 = time.time()
            r = ks.route(intent, tokens_est=200, prefer_free=True)
            dt = (time.time() - t0) * 1000.0
            latencies.append(dt)
            chosen = str(r.get("provider") or (r.get("route") or {}).get("provider") or "")
            if r.get("ok") and chosen:
                ok_n += 1
                used_providers[chosen] = used_providers.get(chosen, 0) + 1
                if chosen != pid:
                    failover_n += 1
            else:
                fail_n += 1
            samples.append(
                {
                    "i": i,
                    "ok": bool(r.get("ok")),
                    "provider": chosen or None,
                    "latency_ms": round(dt, 1),
                    "chaos_target": pid,
                }
            )
            if live_chat and r.get("ok") and chosen:
                try:
                    from tollgate.chat_route import routed_chat

                    routed_chat(
                        "ping",
                        intent=intent,
                        provider=chosen,
                        max_tokens=8,
                        prefer_free=True,
                        consumer="chaos-test",
                        agent_id="chaos-test",
                    )
                except Exception:  # noqa: BLE001
                    pass
    finally:
        stop_chaos(pid, root=root)

    elapsed = time.time() - started
    recovery_ms = min(latencies) if latencies else 0.0
    # rough extra cost: only if live_chat burned paid path — leave 0 for route-only
    report = {
        "ok": fail_n == 0 and ok_n > 0,
        "id": uuid.uuid4().hex[:12],
        "kind": "failover_test",
        "chaos_provider": pid,
        "intent": intent,
        "requests_tested": n,
        "successful": ok_n,
        "failed": fail_n,
        "automatic_failover_pct": round(100.0 * failover_n / n, 1) if n else 0.0,
        "failover_hits": failover_n,
        "stayed_on_chaos_target": used_providers.get(pid, 0),
        "providers_used": used_providers,
        "recovery_time_ms_best": round(recovery_ms, 1),
        "latency_ms_avg": round(sum(latencies) / len(latencies), 1) if latencies else 0.0,
        "elapsed_s": round(elapsed, 2),
        "extra_cost_usd": 0.0,
        "survived": fail_n == 0 and ok_n > 0 and used_providers.get(pid, 0) == 0,
        "message": (
            f"Application survived {pid} outage"
            if fail_n == 0 and ok_n > 0 and used_providers.get(pid, 0) == 0
            else (
                f"Partial: {ok_n}/{n} ok, {used_providers.get(pid, 0)} still hit chaos target"
                if ok_n
                else f"Failed: no successful routes while {pid} was down"
            )
        ),
        "samples": samples[:20],
        "finished_at": time.time(),
    }

    path = chaos_path(root)
    with _LOCK:
        with FileLock(path):
            data = _purge_expired(_load(path))
            data["last_report"] = report
            hist = list(data.get("history") or [])
            hist.append(
                {
                    "id": report["id"],
                    "chaos_provider": pid,
                    "survived": report["survived"],
                    "finished_at": report["finished_at"],
                    "successful": ok_n,
                    "failed": fail_n,
                }
            )
            data["history"] = hist[-50:]
            _write(path, data)

    try:
        from tollgate.audit_log import append_audit

        append_audit(
            "chaos_test",
            provider=pid,
            op="failover_test",
            ok=bool(report["survived"]),
            error="" if report["survived"] else report["message"],
            extra={
                "successful": ok_n,
                "failed": fail_n,
                "failover_pct": report["automatic_failover_pct"],
            },
            root=root,
        )
    except Exception:  # noqa: BLE001
        pass

    return report
