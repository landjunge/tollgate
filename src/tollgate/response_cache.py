"""
Operational response cache — NOT agent memory.

Policy (enforced):
  - only configured ops (default: search, status, quota, models, credits)
  - only request_class free|batch|system (never interactive by default)
  - never high-risk providers
  - cache key includes consumer when configured (avoid cross-consumer bleed on chat-like ops)

Stores provider results (e.g. Brave search JSON), never ledger chat transcripts.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any

from tollgate.app_config import load_config
from tollgate.cost import is_high_risk
from tollgate.gateway.context import RequestClass, RequestContext

_LOCK = threading.RLock()
_STORE: dict[str, tuple[float, dict[str, Any]]] = {}  # key -> (expires_ts, value)


def _cfg() -> dict[str, Any]:
    c = load_config().get("response_cache") or {}
    return c if isinstance(c, dict) else {}


def cache_enabled() -> bool:
    return bool(_cfg().get("enabled", True))


def cache_eligible(
    provider: str,
    op: str,
    *,
    ctx: RequestContext | None = None,
) -> bool:
    if not cache_enabled():
        return False
    pid = (provider or "").strip().lower()
    oname = (op or "").strip().lower()
    if is_high_risk(pid):
        return False
    cfg = _cfg()
    ops = {str(x).lower() for x in (cfg.get("ops") or ["search", "status", "quota", "models", "credits"])}
    if oname not in ops:
        return False
    # chat never unless explicitly listed AND non-interactive
    if oname in ("chat", "complete", "completion") and oname not in ops:
        return False
    ctx = ctx or RequestContext()
    allowed_classes = {
        str(x).lower()
        for x in (cfg.get("request_classes") or ["free", "batch", "system"])
    }
    rclass = (
        ctx.request_class.value
        if isinstance(ctx.request_class, RequestClass)
        else str(ctx.request_class or "interactive")
    ).lower()
    if rclass not in allowed_classes:
        return False
    if rclass == "interactive" and not bool(cfg.get("allow_interactive", False)):
        return False
    return True


def _stable_args(kwargs: dict[str, Any]) -> str:
    # drop non-deterministic / huge fields
    skip = {"tokens_est", "chars_est", "stream", "timeout"}
    clean = {k: v for k, v in sorted(kwargs.items()) if k not in skip}
    try:
        raw = json.dumps(clean, sort_keys=True, default=str, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        raw = repr(clean)
    # hard cap key material size
    return raw[:4000]


def make_key(
    provider: str,
    op: str,
    kwargs: dict[str, Any],
    *,
    consumer: str = "",
) -> str:
    cfg = _cfg()
    parts = [
        (provider or "").strip().lower(),
        (op or "").strip().lower(),
        _stable_args(kwargs),
    ]
    if bool(cfg.get("include_consumer_in_key", True)):
        parts.append((consumer or "").strip()[:64])
    blob = "|".join(parts)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def get(key: str) -> dict[str, Any] | None:
    now = time.time()
    with _LOCK:
        row = _STORE.get(key)
        if not row:
            return None
        exp, val = row
        if exp < now:
            _STORE.pop(key, None)
            return None
        # return shallow copy so callers don't mutate store
        return dict(val)


def put(key: str, value: dict[str, Any]) -> None:
    if not isinstance(value, dict):
        return
    # never cache errors as long-lived "success"
    if value.get("ok") is False:
        return
    ttl = float(_cfg().get("ttl_s") or 300)
    max_entries = int(_cfg().get("max_entries") or 256)
    # strip accidental large free-text if someone stuffed content at top level for chat
    # (search results are structured lists — ok)
    with _LOCK:
        # simple eviction: drop expired then oldest half if over cap
        now = time.time()
        dead = [k for k, (e, _) in _STORE.items() if e < now]
        for k in dead:
            _STORE.pop(k, None)
        if len(_STORE) >= max_entries:
            # drop ~25% oldest by expiry
            ordered = sorted(_STORE.items(), key=lambda kv: kv[1][0])
            for k, _ in ordered[: max(1, max_entries // 4)]:
                _STORE.pop(k, None)
        _STORE[key] = (now + max(1.0, ttl), dict(value))


def clear() -> None:
    with _LOCK:
        _STORE.clear()


def stats() -> dict[str, Any]:
    with _LOCK:
        return {"entries": len(_STORE), "enabled": cache_enabled(), "cfg": _cfg()}
