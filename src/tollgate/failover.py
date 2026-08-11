"""
Execute-time failover across routed candidates.

Router already builds primary + fallbacks under limits. This module decides
when a failed *call* may retry the next candidate (not budget/policy denials).
"""

from __future__ import annotations

from typing import Any

from tollgate.app_config import load_config
from tollgate.gateway.errors import ErrorClass, classify_result

# Failures that are provider-local — try next hop
_RETRIABLE = {
    ErrorClass.PROVIDER_DOWN,
    ErrorClass.RATE_LIMIT,
    ErrorClass.EDGE_BLOCK,
    ErrorClass.AUTH_DEAD,
    ErrorClass.EMPTY_COMPLETION,
    ErrorClass.UNKNOWN,
}

# Never hop: would burn more money or violate local policy
_HARD_STOP = {
    ErrorClass.BUDGET_HARD,
    ErrorClass.POLICY_DENY,
}


def auto_failover_enabled() -> bool:
    return bool(load_config().get("auto_failover", True))


def is_retriable_failure(result: dict[str, Any] | None) -> bool:
    """True if another provider candidate should be attempted."""
    if not isinstance(result, dict):
        return True
    if result.get("ok") is True:
        return False
    # explicit class from gateway
    raw = result.get("error_class") or (result.get("admit") or {}).get("code")
    try:
        if raw:
            ec = ErrorClass(str(raw))
            if ec in _HARD_STOP:
                return False
            if ec in _RETRIABLE:
                return True
            if ec == ErrorClass.OK:
                return False
    except ValueError:
        pass
    ec = classify_result(result)
    if ec in _HARD_STOP:
        return False
    if ec in _RETRIABLE:
        return True
    # empty content treated as retriable
    if result.get("ok") and not str(result.get("content") or "").strip():
        return True
    return ec != ErrorClass.OK


def build_candidates(
    *,
    provider: str = "",
    model: str = "",
    intent: str = "llm",
    tokens_est: int = 0,
    prefer_free: bool | None = None,
    pinned: bool = False,
) -> dict[str, Any]:
    """
    Return candidate list for chat execute.

    If ``provider`` is set (pinned), only that hop is used (no failover),
    unless auto_failover and not pinned via empty provider from client.

    Returns::
      {ok, candidates: [{provider, model}, ...], route?, error?}
    """
    from tollgate import get_keys_service

    pid = (provider or "").strip().lower()
    mid = (model or "").strip()

    # Explicit provider pin: single candidate (caller chose the lane)
    if pid and pinned:
        return {
            "ok": True,
            "candidates": [{"provider": pid, "model": mid}],
            "pinned": True,
            "auto_failover": False,
        }

    if pid and not auto_failover_enabled():
        return {
            "ok": True,
            "candidates": [{"provider": pid, "model": mid}],
            "pinned": True,
            "auto_failover": False,
        }

    # When provider is set without pin flag, still allow multi-hop only if
    # we re-route — actually explicit provider means pin.
    if pid:
        return {
            "ok": True,
            "candidates": [{"provider": pid, "model": mid}],
            "pinned": True,
            "auto_failover": False,
        }

    intent_use = intent
    if prefer_free is True and intent in ("llm", "paid_llm"):
        intent_use = "free_llm"
    route = get_keys_service().route(
        intent_use,
        tokens_est=tokens_est,
        live=False,
        prefer_free=prefer_free,
    )
    if not route.get("ok"):
        return {
            "ok": False,
            "error": route.get("error") or "no provider for intent",
            "route": route,
            "candidates": [],
        }

    primary = route.get("route") if isinstance(route.get("route"), dict) else {}
    cands: list[dict[str, str]] = []
    p0 = str(route.get("provider") or primary.get("provider") or "").strip().lower()
    m0 = mid or str(route.get("model") or primary.get("model") or "").strip()
    if p0:
        cands.append({"provider": p0, "model": m0})

    if auto_failover_enabled():
        for fb in route.get("fallbacks") or []:
            if not isinstance(fb, dict):
                continue
            fp = str(fb.get("provider") or "").strip().lower()
            fm = str(fb.get("model") or "").strip()
            if not fp:
                continue
            if any(c["provider"] == fp for c in cands):
                continue
            cands.append({"provider": fp, "model": fm or m0})

    if not cands:
        return {
            "ok": False,
            "error": "router returned empty provider",
            "route": route,
            "candidates": [],
        }

    return {
        "ok": True,
        "candidates": cands,
        "route": route,
        "pinned": False,
        "auto_failover": auto_failover_enabled(),
    }


def annotate_success(
    result: dict[str, Any],
    *,
    tried: list[dict[str, Any]],
    provider: str,
    model: str,
) -> dict[str, Any]:
    out = dict(result)
    out["provider"] = out.get("provider") or provider
    out["model"] = out.get("model") or model
    out["failover"] = {
        "tried": tried,
        "winner": provider,
        "hops": len(tried),
    }
    return out


def annotate_failure(
    last: dict[str, Any] | None,
    *,
    tried: list[dict[str, Any]],
) -> dict[str, Any]:
    last = dict(last or {})
    last.setdefault("ok", False)
    last.setdefault("error", "all failover candidates failed")
    last["failover"] = {
        "tried": tried,
        "winner": None,
        "hops": len(tried),
        "exhausted": True,
    }
    return last
