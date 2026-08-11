"""
Token / call / char ledger — daily buckets, persistent.

File: <WS>/User/keys_usage.json
"""

from __future__ import annotations

import json
import threading
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from tollgate.filelock import FileLock
from tollgate.paths import user_dir

_LOCK = threading.RLock()
USAGE_NAME = "keys_usage.json"


def _today() -> str:
    return date.today().isoformat()


def usage_path(root: Path | None = None) -> Path:
    return (user_dir(root) / USAGE_NAME).resolve()


def _empty_day(day: str | None = None) -> dict[str, Any]:
    return {
        "day": day or _today(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "providers": {},
        "consumers": {},
        "totals": {
            "calls": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "tokens": 0,
            "chars": 0,
            "usd": 0.0,
            "errors": 0,
        },
    }


def _empty_provider() -> dict[str, Any]:
    return {
        "calls": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "tokens": 0,
        "chars": 0,
        "usd": 0.0,
        "errors": 0,
        "last_call_ts": 0.0,
        "by_op": {},
        # ops health (not agent memory)
        "latency_ms_sum": 0.0,
        "latency_ms_n": 0,
        "latency_ms_last": 0.0,
    }


def _empty_consumer() -> dict[str, Any]:
    """Per-consumer day counters (same shape as provider, no by_op noise)."""
    return {
        "calls": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "tokens": 0,
        "chars": 0,
        "usd": 0.0,
        "errors": 0,
        "last_call_ts": 0.0,
    }


def _norm_consumer(consumer: str | None) -> str:
    cid = (consumer or "").strip()[:64]
    if not cid or cid in ("anonymous", "*"):
        return "anonymous"
    return cid


def load_usage(*, root: Path | None = None) -> dict[str, Any]:
    path = usage_path(root)
    with _LOCK:
        with FileLock(path):
            return _load_unlocked(path)


def _corrupt_day(reason: str) -> dict[str, Any]:
    """Fail-closed marker — never treat as empty (would reset budgets)."""
    d = _empty_day()
    d["_corrupt"] = True
    d["_corrupt_reason"] = reason[:200]
    return d


def is_ledger_corrupt(data: dict[str, Any] | None) -> bool:
    return bool(data and data.get("_corrupt"))


def _load_unlocked(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return _empty_day()
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        return _corrupt_day(f"json_parse: {e}")
    if not isinstance(data, dict):
        return _corrupt_day("not_an_object")
    if data.get("_corrupt"):
        return data
    if data.get("day") != _today():
        # intentional day rollover — not corruption
        data = _empty_day()
        _write_unlocked(path, data)
    return data


def _write(path: Path, data: dict[str, Any]) -> None:
    with FileLock(path):
        _write_unlocked(path, data)


def _write_unlocked(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def provider_usage(provider_id: str, *, root: Path | None = None) -> dict[str, Any]:
    data = load_usage(root=root)
    p = (data.get("providers") or {}).get(provider_id) or _empty_provider()
    return dict(p)


def consumer_usage(consumer: str, *, root: Path | None = None) -> dict[str, Any]:
    """Today's usage for one consumer lane (n8n, gnom, …)."""
    data = load_usage(root=root)
    cid = _norm_consumer(consumer)
    c = (data.get("consumers") or {}).get(cid) or _empty_consumer()
    return dict(c)


def record_usage(
    provider_id: str,
    *,
    op: str = "call",
    tokens_in: int = 0,
    tokens_out: int = 0,
    chars: int = 0,
    usd: float = 0.0,
    error: bool = False,
    root: Path | None = None,
    meta: dict[str, Any] | None = None,
    consumer: str = "",
    latency_ms: float = 0.0,
) -> dict[str, Any]:
    """
    Atomic-ish append to today's ledger.

    Operational counters only. ``meta`` is sanitized — no chat/transcript/content
    (see ops_boundary.sanitize_meta). This is not agent memory.

    When ``consumer`` is set, also increments the per-consumer day envelope counters.
    ``latency_ms`` feeds provider health averages (control plane).
    """
    from tollgate.ops_boundary import sanitize_meta

    path = usage_path(root)
    tin = max(0, int(tokens_in or 0))
    tout = max(0, int(tokens_out or 0))
    ch = max(0, int(chars or 0))
    usd_v = max(0.0, float(usd or 0.0))
    lat = max(0.0, float(latency_ms or 0.0))
    cid = _norm_consumer(consumer)
    if usd_v <= 0.0 and (tin or tout):
        try:
            from tollgate.cost import estimate_usd

            usd_v = estimate_usd(provider_id, tokens_in=tin, tokens_out=tout)
        except Exception:  # noqa: BLE001
            usd_v = 0.0
    safe_meta = sanitize_meta(meta)
    # One cross-process critical section (avoid nested FileLock deadlocks)
    with _LOCK:
        with FileLock(path):
            data = _load_unlocked(path)
            if is_ledger_corrupt(data):
                try:
                    from tollgate.audit_log import append_audit

                    append_audit(
                        "ledger_corrupt",
                        provider=provider_id,
                        op=op,
                        consumer=cid,
                        error=str(data.get("_corrupt_reason") or "corrupt"),
                        ok=False,
                        root=root,
                    )
                except Exception:  # noqa: BLE001
                    pass
                return {
                    "ok": False,
                    "error": "ledger corrupt — fail-closed (fix keys_usage.json)",
                    "_corrupt": True,
                }
            if data.get("day") != _today():
                data = _empty_day()
            providers = data.setdefault("providers", {})
            p = providers.get(provider_id) or _empty_provider()
            p["calls"] = int(p.get("calls") or 0) + 1
            p["tokens_in"] = int(p.get("tokens_in") or 0) + tin
            p["tokens_out"] = int(p.get("tokens_out") or 0) + tout
            p["tokens"] = int(p.get("tokens") or 0) + tin + tout
            p["chars"] = int(p.get("chars") or 0) + ch
            p["usd"] = float(p.get("usd") or 0.0) + usd_v
            if error:
                p["errors"] = int(p.get("errors") or 0) + 1
            p["last_call_ts"] = time.time()
            if lat > 0:
                p["latency_ms_sum"] = float(p.get("latency_ms_sum") or 0.0) + lat
                p["latency_ms_n"] = int(p.get("latency_ms_n") or 0) + 1
                p["latency_ms_last"] = lat
            by_op = p.setdefault("by_op", {})
            slot = by_op.get(op) or {"calls": 0, "tokens": 0, "chars": 0, "usd": 0.0}
            slot["calls"] = int(slot.get("calls") or 0) + 1
            slot["tokens"] = int(slot.get("tokens") or 0) + tin + tout
            slot["chars"] = int(slot.get("chars") or 0) + ch
            slot["usd"] = float(slot.get("usd") or 0.0) + usd_v
            by_op[op] = slot
            if safe_meta:
                p["last_meta"] = safe_meta
            for bad in ("content", "message", "messages", "prompt", "transcript", "query"):
                p.pop(bad, None)
            providers[provider_id] = p

            # Per-consumer lane (n8n / gnom / openai:… labels)
            consumers = data.setdefault("consumers", {})
            cu = consumers.get(cid) or _empty_consumer()
            cu["calls"] = int(cu.get("calls") or 0) + 1
            cu["tokens_in"] = int(cu.get("tokens_in") or 0) + tin
            cu["tokens_out"] = int(cu.get("tokens_out") or 0) + tout
            cu["tokens"] = int(cu.get("tokens") or 0) + tin + tout
            cu["chars"] = int(cu.get("chars") or 0) + ch
            cu["usd"] = float(cu.get("usd") or 0.0) + usd_v
            if error:
                cu["errors"] = int(cu.get("errors") or 0) + 1
            cu["last_call_ts"] = time.time()
            consumers[cid] = cu

            tot = data.setdefault("totals", _empty_day()["totals"])
            tot["calls"] = int(tot.get("calls") or 0) + 1
            tot["tokens_in"] = int(tot.get("tokens_in") or 0) + tin
            tot["tokens_out"] = int(tot.get("tokens_out") or 0) + tout
            tot["tokens"] = int(tot.get("tokens") or 0) + tin + tout
            tot["chars"] = int(tot.get("chars") or 0) + ch
            tot["usd"] = float(tot.get("usd") or 0.0) + usd_v
            if error:
                tot["errors"] = int(tot.get("errors") or 0) + 1
            _write_unlocked(path, data)
            try:
                from tollgate.audit_log import append_audit

                append_audit(
                    "usage",
                    provider=provider_id,
                    op=op,
                    consumer=cid,
                    tokens=tin + tout,
                    usd=usd_v,
                    ok=not error,
                    error="error" if error else "",
                    root=root,
                )
            except Exception:  # noqa: BLE001
                pass
            out = dict(p)
            out["consumer"] = cid
            out["consumer_usage"] = dict(cu)
            return out


def extract_tokens_from_result(result: Any) -> tuple[int, int, int]:
    """
    Best-effort parse provider result → (tokens_in, tokens_out, chars).

    Supports OpenAI-style usage, EL char counts, Brave (0 tokens).
    """
    if not isinstance(result, dict):
        return 0, 0, 0
    usage = result.get("usage")
    if isinstance(usage, dict):
        tin = int(
            usage.get("prompt_tokens")
            or usage.get("input_tokens")
            or usage.get("prompt_tokens_details", {}).get("cached_tokens")
            or 0
        )
        # prefer explicit fields
        tin = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        tout = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        if tin or tout:
            return tin, tout, 0
        total = int(usage.get("total_tokens") or 0)
        if total:
            return total, 0, 0

    # nested data.usage (some wrappers)
    data = result.get("data")
    if isinstance(data, dict) and isinstance(data.get("usage"), dict):
        return extract_tokens_from_result({"usage": data["usage"]})

    # ElevenLabs budget style
    if "character_count" in result or result.get("op") == "budget":
        return 0, 0, 0
    # TTS / search cost estimate fields
    cost_chars = result.get("cost")
    if isinstance(cost_chars, (int, float)) and result.get("provider") == "elevenlabs":
        return 0, 0, int(cost_chars)

    # explicit
    tin = int(result.get("tokens_in") or 0)
    tout = int(result.get("tokens_out") or 0)
    chars = int(result.get("chars") or result.get("character_count_delta") or 0)
    return tin, tout, chars


def usage_summary(*, root: Path | None = None) -> dict[str, Any]:
    data = load_usage(root=root)
    return {
        "ok": True,
        "day": data.get("day"),
        "updated_at": data.get("updated_at"),
        "totals": data.get("totals") or {},
        "providers": data.get("providers") or {},
        "consumers": data.get("consumers") or {},
        "path": str(usage_path(root)),
    }
