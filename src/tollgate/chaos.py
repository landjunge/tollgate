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
    return {
        "version": 1,
        "active": [],
        "recovering": [],
        "last_report": None,
        "history": [],
    }


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return _empty()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return _empty()
        raw.setdefault("active", [])
        raw.setdefault("recovering", [])
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
    recovering = []
    for row in data.get("recovering") or []:
        if not isinstance(row, dict):
            continue
        started = float(row.get("started_at") or 0)
        dur = float(row.get("duration_s") or 0)
        if dur <= 0 or (started + dur) > now:
            recovering.append(row)
    data["recovering"] = recovering
    return data


def reliability_policy() -> dict[str, Any]:
    """keys_app.reliability defaults."""
    try:
        from tollgate.app_config import load_config

        r = (load_config() or {}).get("reliability") or {}
        if not isinstance(r, dict):
            r = {}
    except Exception:  # noqa: BLE001
        r = {}
    return {
        "availability_target": float(r.get("availability_target") or 99.9),
        "max_failover_time_s": float(r.get("max_failover_time_s") or 5.0),
        "required_fallbacks": int(r.get("required_fallbacks") or 2),
        "gradual_recovery_s": float(r.get("gradual_recovery_s") or 60.0),
    }


def status(*, root: Path | None = None) -> dict[str, Any]:
    path = chaos_path(root)
    with _LOCK:
        with FileLock(path):
            data = _purge_expired(_load(path))
            _write(path, data)
            hist = list(data.get("history") or [])
            return {
                "ok": True,
                "active": list(data.get("active") or []),
                "recovering": list(data.get("recovering") or []),
                "last_report": data.get("last_report"),
                "history": hist[-20:],
                "policy": reliability_policy(),
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


def _recovery_progress(row: dict[str, Any], *, now: float | None = None) -> float:
    """0.0 = fully divert, 1.0 = full traffic restored."""
    now = now if now is not None else time.time()
    started = float(row.get("started_at") or 0)
    dur = float(row.get("duration_s") or 0)
    if dur <= 0:
        return 1.0
    return max(0.0, min(1.0, (now - started) / dur))


def recovery_allow(provider: str, *, root: Path | None = None, salt: str = "") -> bool:
    """
    During gradual recovery, allow a growing fraction of traffic back to provider.
    Deterministic per (provider, second) so multi-worker behavior is stable.
    """
    import hashlib

    pid = (provider or "").strip().lower()
    if not pid:
        return True
    st = status(root=root)
    now = time.time()
    for row in st.get("recovering") or []:
        if str(row.get("provider") or "").lower() != pid:
            continue
        progress = _recovery_progress(row, now=now)
        if progress >= 1.0:
            return True
        if progress <= 0.0:
            return False
        h = int(hashlib.md5(f"{pid}:{int(now)}:{salt}".encode()).hexdigest()[:8], 16)
        return (h % 1000) / 1000.0 < progress
    return True


def is_provider_unavailable(provider: str, *, root: Path | None = None) -> bool:
    """True if chaos inject OR gradual recovery still diverting this request."""
    if is_provider_in_chaos(provider, root=root):
        return True
    # recovering: unavailable when recovery_allow is False
    if not recovery_allow(provider, root=root):
        # only if actually in recovering list
        st = status(root=root)
        pid = (provider or "").strip().lower()
        for row in st.get("recovering") or []:
            if str(row.get("provider") or "").lower() == pid:
                return True
    return False


def start_recovery(
    provider: str,
    *,
    duration_s: float | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Begin gradual traffic ramp after chaos ends."""
    pid = (provider or "").strip().lower()
    if not pid:
        return {"ok": False, "error": "provider required"}
    pol = reliability_policy()
    dur = float(duration_s) if duration_s is not None else float(pol["gradual_recovery_s"])
    if dur <= 0:
        return {"ok": True, "skipped": True, "reason": "gradual_recovery_s=0"}
    path = chaos_path(root)
    with _LOCK:
        with FileLock(path):
            data = _purge_expired(_load(path))
            data["recovering"] = [
                r
                for r in (data.get("recovering") or [])
                if str(r.get("provider") or "").lower() != pid
            ]
            row = {
                "provider": pid,
                "started_at": time.time(),
                "duration_s": dur,
                "mode": "gradual",
            }
            data["recovering"].append(row)
            _write(path, data)
            return {"ok": True, "recovery": row}


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
    try:
        from tollgate.alerts import maybe_alert

        maybe_alert(
            "chaos_started",
            provider=pid,
            message=f"chaos inject {pid} for {dur:.0f}s ({reason})",
            extra={"duration_s": dur, "reason": reason},
        )
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "inject": row, "path": str(path)}


def stop_chaos(
    provider: str = "",
    *,
    all_injects: bool = False,
    start_gradual_recovery: bool = True,
    root: Path | None = None,
) -> dict[str, Any]:
    path = chaos_path(root)
    stopped_providers: list[str] = []
    with _LOCK:
        with FileLock(path):
            data = _purge_expired(_load(path))
            before = list(data.get("active") or [])
            if all_injects or not (provider or "").strip():
                stopped_providers = [
                    str(r.get("provider") or "") for r in before if r.get("provider")
                ]
                data["active"] = []
            else:
                pid = provider.strip().lower()
                stopped_providers = [
                    str(r.get("provider") or "")
                    for r in before
                    if str(r.get("provider") or "").lower() == pid
                ]
                data["active"] = [
                    r
                    for r in before
                    if str(r.get("provider") or "").lower() != pid
                ]
            _write(path, data)
    recoveries = []
    if start_gradual_recovery:
        for pid in stopped_providers:
            if pid:
                recoveries.append(start_recovery(pid, root=root))
    try:
        from tollgate.alerts import maybe_alert

        for pid in stopped_providers:
            if pid:
                maybe_alert(
                    "chaos_stopped",
                    provider=pid,
                    message=f"chaos inject stopped on {pid}",
                    extra={"gradual_recovery": start_gradual_recovery},
                )
    except Exception:  # noqa: BLE001
        pass
    return {
        "ok": True,
        "stopped": len(stopped_providers),
        "active": status(root=root).get("active") or [],
        "recovering": status(root=root).get("recovering") or [],
        "recoveries": recoveries,
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
    # Key.txt → env so inventory/route see DEEPSEEK_*/OPENCODE_* during CLI chaos
    try:
        from tollgate.secrets import ensure_env_from_key_txt, load_keys

        ensure_env_from_key_txt(root)
        load_keys(root)
    except Exception:  # noqa: BLE001
        pass
    pid = (provider or "").strip().lower()
    if not pid:
        return {"ok": False, "error": "provider required"}
    n = max(1, min(100, int(requests or 5)))
    started = time.time()
    pol = reliability_policy()
    inj = start_chaos(pid, duration_s=duration_s, reason="failover_test", root=root)
    if not inj.get("ok"):
        return inj

    # baseline $ for chaos-test consumer (extra cost after live_chat)
    usd_before = 0.0
    try:
        from tollgate.usage_ledger import consumer_usage

        usd_before = float(consumer_usage("chaos-test", root=root).get("usd") or 0.0)
    except Exception:  # noqa: BLE001
        usd_before = 0.0

    ks = get_keys_service()
    # Fresh inventory after keys load (avoid stale "key missing" cards)
    try:
        ks.inventory(live=False, use_cache=False)
    except Exception:  # noqa: BLE001
        pass
    ok_n = 0
    fail_n = 0
    failover_n = 0
    used_providers: dict[str, int] = {}
    latencies: list[float] = []
    samples: list[dict[str, Any]] = []

    last_route_error = ""
    last_tried: list[Any] = []
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
                last_route_error = str(r.get("error") or "route failed")
                tried = r.get("tried") if isinstance(r.get("tried"), list) else []
                if tried:
                    last_tried = tried
            samples.append(
                {
                    "i": i,
                    "ok": bool(r.get("ok")),
                    "provider": chosen or None,
                    "latency_ms": round(dt, 1),
                    "chaos_target": pid,
                    "error": (None if (r.get("ok") and chosen) else (r.get("error") or None)),
                    "tried": (r.get("tried") or [])[:6]
                    if not (r.get("ok") and chosen)
                    else None,
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
        # recovery ramp starts automatically when inject ends
        stop_chaos(pid, start_gradual_recovery=True, root=root)

    elapsed = time.time() - started
    recovery_ms = min(latencies) if latencies else 0.0
    usd_after = usd_before
    try:
        from tollgate.usage_ledger import consumer_usage

        usd_after = float(consumer_usage("chaos-test", root=root).get("usd") or 0.0)
    except Exception:  # noqa: BLE001
        pass
    extra_cost = max(0.0, usd_after - usd_before)
    max_fo_ms = float(pol["max_failover_time_s"]) * 1000.0
    within_sla = recovery_ms <= max_fo_ms if latencies else False
    survived = fail_n == 0 and ok_n > 0 and used_providers.get(pid, 0) == 0
    # Human next step when no route succeeded (usually: fallbacks lack keys)
    skip_hints: list[str] = []
    for row in last_tried:
        if not isinstance(row, dict):
            continue
        p = str(row.get("provider") or "")
        skip = str(row.get("skip") or row.get("reason") or "")
        if p and skip:
            skip_hints.append(f"{p}: {skip}")
    if not survived and not ok_n:
        next_step = (
            "Fallbacks could not admit while primary was injected down. "
            "Need a second provider with a key on this intent. "
            f"Try: tollgate chaos test {pid} --intent llm --requests 8 "
            "(llm chain usually includes deepseek). "
            "Or set OPENROUTER/NVIDIA keys for free_llm."
        )
        if skip_hints:
            next_step = "Skipped during inject: " + "; ".join(skip_hints[:6]) + ". " + next_step
        fail_msg = (
            f"Failed: no successful routes while {pid} was down"
            + (f" ({last_route_error})" if last_route_error else "")
        )
    elif not survived and ok_n:
        next_step = (
            f"Partial failover ({ok_n}/{n}). Tighten free_llm chain or re-run "
            f"with more requests. Check circuits: tollgate circuits list"
        )
        fail_msg = (
            f"Partial: {ok_n}/{n} ok, {used_providers.get(pid, 0)} still hit chaos target"
        )
    else:
        next_step = None
        fail_msg = ""

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
        "extra_cost_usd": round(extra_cost, 6),
        "policy": {
            "max_failover_time_s": pol["max_failover_time_s"],
            "within_max_failover_time": within_sla,
            "gradual_recovery_s": pol["gradual_recovery_s"],
            "availability_target": pol["availability_target"],
        },
        "survived": survived,
        "next_step": next_step,
        "route_error": last_route_error or None,
        "tried_on_fail": last_tried[:8] if last_tried else None,
        "message": (
            f"Application survived {pid} outage"
            + (f" · extra cost ${extra_cost:.4f}" if extra_cost else "")
            + (
                f" · recovery {recovery_ms:.0f}ms ≤ {max_fo_ms:.0f}ms SLA"
                if survived and within_sla
                else (
                    f" · recovery {recovery_ms:.0f}ms > {max_fo_ms:.0f}ms SLA"
                    if survived and latencies
                    else ""
                )
            )
            if survived
            else fail_msg
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

    try:
        from tollgate.alerts import maybe_alert

        maybe_alert(
            "chaos_dr_survived" if report["survived"] else "chaos_dr_failed",
            provider=pid,
            message=str(report.get("message") or ""),
            extra={
                "successful": ok_n,
                "failed": fail_n,
                "survived": report["survived"],
                "recovery_time_ms_best": report.get("recovery_time_ms_best"),
            },
            force=True,
        )
    except Exception:  # noqa: BLE001
        pass

    return report
