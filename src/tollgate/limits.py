"""Enforce per-provider call / token / char limits from app_config."""

from __future__ import annotations

import time
from typing import Any

from tollgate.app_config import is_provider_enabled, load_config, provider_cfg
from tollgate.cost import check_cost_guard
from tollgate.usage_ledger import provider_usage


def check_limits(
    provider_id: str,
    *,
    tokens_est: int = 0,
    chars_est: int = 0,
    op: str = "call",
) -> dict[str, Any]:
    """
    Return {allowed, reason?, remaining_calls, remaining_tokens, wait_ms, remaining_usd}.

    Does not record usage — call after success via record_usage.
    """
    cfg = load_config()
    if not bool(cfg.get("record_usage", True)):
        # limits still apply if provider block exists
        pass

    # Cost guard first (Google high-risk, max_usd_day)
    cg = check_cost_guard(provider_id, tokens_est=tokens_est)
    if not cg.get("allowed"):
        return {
            "allowed": False,
            "reason": cg.get("reason"),
            "remaining_calls": 0,
            "remaining_tokens": 0,
            "remaining_usd": cg.get("remaining_usd"),
            "high_risk": cg.get("high_risk"),
            "wait_ms": 0,
        }

    if not is_provider_enabled(provider_id):
        return {
            "allowed": False,
            "reason": f"provider {provider_id} disabled in keys_app.json",
            "remaining_calls": 0,
            "remaining_tokens": 0,
            "remaining_usd": cg.get("remaining_usd"),
            "wait_ms": 0,
        }

    pcfg = provider_cfg(provider_id)
    if not pcfg:
        return {
            "allowed": True,
            "reason": None,
            "remaining_calls": None,
            "remaining_tokens": None,
            "wait_ms": 0,
        }

    usage = provider_usage(provider_id)
    calls = int(usage.get("calls") or 0)
    tokens = int(usage.get("tokens") or 0)
    chars = int(usage.get("chars") or 0)
    last_ts = float(usage.get("last_call_ts") or 0)

    max_calls = int(pcfg.get("max_calls_day") or 0)
    max_tokens = int(pcfg.get("max_tokens_day") or 0)
    max_call_tokens = int(pcfg.get("max_tokens_call") or 0)
    max_chars = int(pcfg.get("max_chars_day") or 0)
    min_interval = int(pcfg.get("min_interval_ms") or 0)

    # interval
    wait_ms = 0
    if min_interval > 0 and last_ts > 0:
        elapsed_ms = int((time.time() - last_ts) * 1000)
        if elapsed_ms < min_interval:
            wait_ms = min_interval - elapsed_ms
            return {
                "allowed": False,
                "reason": f"min_interval_ms={min_interval} — wait {wait_ms}ms",
                "remaining_calls": max(0, max_calls - calls) if max_calls else None,
                "remaining_tokens": max(0, max_tokens - tokens) if max_tokens else None,
                "wait_ms": wait_ms,
            }

    if max_calls > 0 and calls >= max_calls:
        return {
            "allowed": False,
            "reason": f"max_calls_day reached ({calls}/{max_calls})",
            "remaining_calls": 0,
            "remaining_tokens": max(0, max_tokens - tokens) if max_tokens else None,
            "wait_ms": 0,
        }

    est = max(0, int(tokens_est or 0))
    if max_call_tokens > 0 and est > max_call_tokens:
        return {
            "allowed": False,
            "reason": f"max_tokens_call {est} > {max_call_tokens}",
            "remaining_calls": max(0, max_calls - calls) if max_calls else None,
            "remaining_tokens": max(0, max_tokens - tokens) if max_tokens else None,
            "wait_ms": 0,
        }

    if max_tokens > 0 and (tokens + est) > max_tokens:
        return {
            "allowed": False,
            "reason": f"max_tokens_day would exceed ({tokens}+{est}/{max_tokens})",
            "remaining_calls": max(0, max_calls - calls) if max_calls else None,
            "remaining_tokens": max(0, max_tokens - tokens),
            "wait_ms": 0,
        }

    ch_est = max(0, int(chars_est or 0))
    if max_chars > 0 and (chars + ch_est) > max_chars:
        return {
            "allowed": False,
            "reason": f"max_chars_day would exceed ({chars}+{ch_est}/{max_chars})",
            "remaining_calls": max(0, max_calls - calls) if max_calls else None,
            "remaining_tokens": max(0, max_tokens - tokens) if max_tokens else None,
            "remaining_chars": max(0, max_chars - chars),
            "wait_ms": 0,
        }

    return {
        "allowed": True,
        "reason": None,
        "remaining_calls": (max_calls - calls) if max_calls else None,
        "remaining_tokens": (max_tokens - tokens) if max_tokens else None,
        "remaining_chars": (max_chars - chars) if max_chars else None,
        "remaining_usd": cg.get("remaining_usd"),
        "high_risk": cg.get("high_risk"),
        "used": {
            "calls": calls,
            "tokens": tokens,
            "chars": chars,
            "usd": float(usage.get("usd") or 0),
            "op": op,
        },
        "wait_ms": 0,
        "limits": {
            "max_calls_day": max_calls or None,
            "max_tokens_day": max_tokens or None,
            "max_chars_day": max_chars or None,
            "max_tokens_call": max_call_tokens or None,
            "max_usd_day": float(pcfg.get("max_usd_day") or 0) or None,
            "min_interval_ms": min_interval or None,
        },
    }
