"""Enforce per-provider and per-consumer call / token / char limits from app_config."""

from __future__ import annotations

import time
from typing import Any

from tollgate.app_config import is_provider_enabled, load_config, provider_cfg
from tollgate.cost import check_cost_guard
from tollgate.usage_ledger import consumer_usage, provider_usage
from tollgate.consumers import normalize_consumer_id


def _as_str_list(val: Any) -> list[str]:
    """Normalize config list/string → lowercased unique tokens."""
    if val is None or val is False:
        return []
    if isinstance(val, str):
        parts = [p.strip().lower() for p in val.replace(";", ",").split(",")]
        return [p for p in parts if p]
    if isinstance(val, (list, tuple, set)):
        out: list[str] = []
        for x in val:
            s = str(x or "").strip().lower()
            if s and s not in out:
                out.append(s)
        return out
    return []


def consumer_envelope(consumer: str) -> dict[str, Any]:
    """
    Resolve day + agent-protection caps + scopes for a consumer id.

    Lookup order: consumer_envelopes.<id> → consumer_envelopes._default → empty.
    Values of 0 / missing mean unlimited at that dimension.
    Empty scope lists mean unrestricted on that axis.
    """
    cfg = load_config()
    envelopes = cfg.get("consumer_envelopes") or {}
    if not isinstance(envelopes, dict):
        return {}
    cid = normalize_consumer_id(consumer)
    block = envelopes.get(cid)
    if not isinstance(block, dict):
        block = envelopes.get("_default")
    if not isinstance(block, dict):
        return {}
    return {
        "max_calls_day": int(block.get("max_calls_day") or 0),
        "max_tokens_day": int(block.get("max_tokens_day") or 0),
        "max_usd_day": float(block.get("max_usd_day") or 0.0),
        # Agent protection (loop / runaway)
        "max_usd_request": float(block.get("max_usd_request") or 0.0),
        "max_usd_hour": float(block.get("max_usd_hour") or 0.0),
        "max_requests_minute": int(block.get("max_requests_minute") or 0),
        "max_tokens_request": int(block.get("max_tokens_request") or 0),
        "max_tool_calls": int(block.get("max_tool_calls") or 0),
        # L3 scopes (allow/block lists — empty allow = unrestricted)
        "allowed_providers": _as_str_list(block.get("allowed_providers")),
        "blocked_providers": _as_str_list(block.get("blocked_providers")),
        "allowed_ops": _as_str_list(block.get("allowed_ops")),
        "blocked_ops": _as_str_list(block.get("blocked_ops")),
        "allowed_intents": _as_str_list(block.get("allowed_intents")),
        "blocked_intents": _as_str_list(block.get("blocked_intents")),
        "consumer": cid,
    }


def _scope_lists_active(env: dict[str, Any]) -> bool:
    keys = (
        "allowed_providers",
        "blocked_providers",
        "allowed_ops",
        "blocked_ops",
        "allowed_intents",
        "blocked_intents",
    )
    return any(bool(env.get(k)) for k in keys)


def _protection_active(env: dict[str, Any]) -> bool:
    keys = (
        "max_calls_day",
        "max_tokens_day",
        "max_usd_day",
        "max_usd_request",
        "max_usd_hour",
        "max_requests_minute",
        "max_tokens_request",
        "max_tool_calls",
    )
    return any(float(env.get(k) or 0) > 0 for k in keys) or _scope_lists_active(env)


def check_consumer_scope(
    consumer: str,
    *,
    provider: str = "",
    op: str = "",
    intent: str = "",
) -> dict[str, Any]:
    """
    L3 consumer scopes — which providers / ops / intents a lane may use.

    Rules (per axis): blocked_* always denies; if allowed_* non-empty, must match.
    Empty lists on an axis = no restriction for that axis.
    """
    cid = normalize_consumer_id(consumer)
    env = consumer_envelope(cid)
    pid = (provider or "").strip().lower()
    op_n = (op or "").strip().lower()
    intent_n = (intent or "").strip().lower()

    def _deny(reason: str, *, field: str) -> dict[str, Any]:
        return {
            "allowed": False,
            "reason": reason,
            "consumer": cid,
            "protection": "scope",
            "scope_field": field,
            "envelope": env,
            "soft_warn": False,
            "wait_ms": 0,
        }

    if pid:
        blocked = env.get("blocked_providers") or []
        allowed = env.get("allowed_providers") or []
        if pid in blocked:
            return _deny(
                f"scope: consumer {cid} blocked_providers includes {pid}",
                field="blocked_providers",
            )
        if allowed and pid not in allowed:
            return _deny(
                f"scope: consumer {cid} provider {pid} not in allowed_providers "
                f"{allowed}",
                field="allowed_providers",
            )

    if op_n:
        blocked = env.get("blocked_ops") or []
        allowed = env.get("allowed_ops") or []
        if op_n in blocked:
            return _deny(
                f"scope: consumer {cid} blocked_ops includes {op_n}",
                field="blocked_ops",
            )
        if allowed and op_n not in allowed:
            return _deny(
                f"scope: consumer {cid} op {op_n} not in allowed_ops {allowed}",
                field="allowed_ops",
            )

    if intent_n:
        blocked = env.get("blocked_intents") or []
        allowed = env.get("allowed_intents") or []
        if intent_n in blocked:
            return _deny(
                f"scope: consumer {cid} blocked_intents includes {intent_n}",
                field="blocked_intents",
            )
        if allowed and intent_n not in allowed:
            return _deny(
                f"scope: consumer {cid} intent {intent_n} not in allowed_intents "
                f"{allowed}",
                field="allowed_intents",
            )

    return {
        "allowed": True,
        "reason": None,
        "consumer": cid,
        "envelope": env if _scope_lists_active(env) else None,
        "soft_warn": False,
        "wait_ms": 0,
    }


def check_consumer_limits(
    consumer: str,
    *,
    tokens_est: int = 0,
    tool_calls_est: int = 0,
    usd_est: float = 0.0,
) -> dict[str, Any]:
    """
    Per-consumer day envelope + agent protection (request/hour/minute).

    Independent of provider caps. 0 limits = pass-through (allowed).
    """
    cid = normalize_consumer_id(consumer)
    env = consumer_envelope(cid)
    max_calls = int(env.get("max_calls_day") or 0)
    max_tokens = int(env.get("max_tokens_day") or 0)
    max_usd = float(env.get("max_usd_day") or 0.0)
    max_usd_req = float(env.get("max_usd_request") or 0.0)
    max_usd_hour = float(env.get("max_usd_hour") or 0.0)
    max_rpm = int(env.get("max_requests_minute") or 0)
    max_tok_req = int(env.get("max_tokens_request") or 0)
    max_tools = int(env.get("max_tool_calls") or 0)
    if not _protection_active(env):
        return {
            "allowed": True,
            "reason": None,
            "consumer": cid,
            "envelope": None,
            "soft_warn": False,
            "wait_ms": 0,
        }

    from tollgate.agent_guard import estimate_request_usd, peek_rates

    est = max(0, int(tokens_est or 0))
    tools = max(0, int(tool_calls_est or 0))
    req_usd = estimate_request_usd(est, usd_hint=float(usd_est or 0.0))

    # ── short windows first for corrupt fail-closed ──────────────────
    rates = peek_rates(cid)
    if rates.get("corrupt"):
        return {
            "allowed": False,
            "reason": (
                "agent_rates corrupt/unreadable — fail-closed "
                f"({rates.get('corrupt_reason') or 'fix agent_rates.json'})"
            ),
            "consumer": cid,
            "protection": "agent_rates",
            "rates_corrupt": True,
            "soft_warn": False,
            "wait_ms": 0,
            "envelope": env,
        }

    # ── per-request hard stops (no ledger needed) ─────────────────────
    if max_tok_req > 0 and est > max_tok_req:
        return {
            "allowed": False,
            "reason": (
                f"agent protection: consumer {cid} max_tokens_request "
                f"{est} > {max_tok_req}"
            ),
            "consumer": cid,
            "protection": "max_tokens_request",
            "soft_warn": False,
            "wait_ms": 0,
            "envelope": env,
        }
    if max_usd_req > 0 and req_usd > max_usd_req:
        return {
            "allowed": False,
            "reason": (
                f"agent protection: consumer {cid} max_usd_request "
                f"est ${req_usd:.4f} > ${max_usd_req}"
            ),
            "consumer": cid,
            "protection": "max_usd_request",
            "soft_warn": False,
            "wait_ms": 0,
            "envelope": env,
        }
    if max_tools > 0 and tools > max_tools:
        return {
            "allowed": False,
            "reason": (
                f"agent protection: consumer {cid} max_tool_calls "
                f"{tools} > {max_tools}"
            ),
            "consumer": cid,
            "protection": "max_tool_calls",
            "soft_warn": False,
            "wait_ms": 0,
            "envelope": env,
        }

    # ── short windows (minute / hour) ─────────────────────────────────
    if max_rpm > 0 and int(rates["minute"]["requests"]) >= max_rpm:
        return {
            "allowed": False,
            "reason": (
                f"agent protection: consumer {cid} max_requests_minute "
                f"reached ({rates['minute']['requests']}/{max_rpm})"
            ),
            "consumer": cid,
            "protection": "max_requests_minute",
            "soft_warn": False,
            "wait_ms": 1000,
            "envelope": env,
            "rates": rates,
        }
    hour_usd = float(rates["hour"]["usd"] or 0.0)
    if max_usd_hour > 0 and (hour_usd + req_usd) > max_usd_hour:
        return {
            "allowed": False,
            "reason": (
                f"agent protection: consumer {cid} max_usd_hour would exceed "
                f"(${hour_usd:.4f}+${req_usd:.4f}/${max_usd_hour})"
            ),
            "consumer": cid,
            "protection": "max_usd_hour",
            "soft_warn": False,
            "wait_ms": 0,
            "envelope": env,
            "rates": rates,
        }

    if max_calls <= 0 and max_tokens <= 0 and max_usd <= 0:
        # only short-window protection configured
        return {
            "allowed": True,
            "reason": None,
            "consumer": cid,
            "envelope": env,
            "soft_warn": False,
            "wait_ms": 0,
            "rates": rates,
            "request_usd_est": req_usd,
        }

    try:
        from tollgate.usage_ledger import is_ledger_corrupt, load_usage

        day = load_usage()
        if is_ledger_corrupt(day):
            return {
                "allowed": False,
                "reason": (
                    "ledger corrupt/unreadable — fail-closed "
                    f"({day.get('_corrupt_reason') or 'fix keys_usage.json'})"
                ),
                "consumer": cid,
                "remaining_calls": 0,
                "remaining_tokens": 0,
                "remaining_usd": 0.0,
                "ledger_corrupt": True,
                "soft_warn": False,
                "wait_ms": 0,
            }
    except Exception as e:  # noqa: BLE001
        return {
            "allowed": False,
            "reason": f"ledger unavailable — fail-closed ({e})",
            "consumer": cid,
            "remaining_calls": 0,
            "remaining_tokens": 0,
            "remaining_usd": 0.0,
            "ledger_corrupt": True,
            "soft_warn": False,
            "wait_ms": 0,
        }

    usage = consumer_usage(cid)
    calls = int(usage.get("calls") or 0)
    tokens = int(usage.get("tokens") or 0)
    usd = float(usage.get("usd") or 0.0)
    # est / rates already computed above for protection

    if max_calls > 0 and calls >= max_calls:
        return {
            "allowed": False,
            "reason": f"consumer {cid} max_calls_day reached ({calls}/{max_calls})",
            "consumer": cid,
            "remaining_calls": 0,
            "remaining_tokens": max(0, max_tokens - tokens) if max_tokens else None,
            "remaining_usd": max(0.0, max_usd - usd) if max_usd else None,
            "soft_warn": False,
            "wait_ms": 0,
            "envelope": env,
            "used": {"calls": calls, "tokens": tokens, "usd": usd},
        }

    if max_tokens > 0 and (tokens + est) > max_tokens:
        return {
            "allowed": False,
            "reason": (
                f"consumer {cid} max_tokens_day would exceed "
                f"({tokens}+{est}/{max_tokens})"
            ),
            "consumer": cid,
            "remaining_calls": max(0, max_calls - calls) if max_calls else None,
            "remaining_tokens": max(0, max_tokens - tokens),
            "remaining_usd": max(0.0, max_usd - usd) if max_usd else None,
            "soft_warn": False,
            "wait_ms": 0,
            "envelope": env,
            "used": {"calls": calls, "tokens": tokens, "usd": usd},
        }

    if max_usd > 0 and usd >= max_usd:
        return {
            "allowed": False,
            "reason": f"consumer {cid} max_usd_day reached ({usd:.4f}/{max_usd})",
            "consumer": cid,
            "remaining_calls": max(0, max_calls - calls) if max_calls else None,
            "remaining_tokens": max(0, max_tokens - tokens) if max_tokens else None,
            "remaining_usd": 0.0,
            "soft_warn": False,
            "wait_ms": 0,
            "envelope": env,
            "used": {"calls": calls, "tokens": tokens, "usd": usd},
        }

    rem_calls = (max_calls - calls) if max_calls else None
    rem_tokens = (max_tokens - tokens) if max_tokens else None
    rem_usd = (max_usd - usd) if max_usd else None

    soft = False
    soft_reason = ""
    ratio = 0.0
    if max_usd > 0:
        ratio = usd / max_usd
        if ratio >= 0.8 or (rem_usd is not None and rem_usd < 0.1):
            soft = True
            soft_reason = f"consumer {cid} usd budget {ratio:.0%}"
    if max_calls > 0 and rem_calls is not None and rem_calls < 5:
        soft = True
        soft_reason = soft_reason or f"consumer {cid} remaining_calls={rem_calls}"

    return {
        "allowed": True,
        "reason": None,
        "consumer": cid,
        "remaining_calls": rem_calls,
        "remaining_tokens": rem_tokens,
        "remaining_usd": rem_usd,
        "soft_warn": soft,
        "soft_reason": soft_reason or None,
        "budget_ratio": ratio if max_usd else None,
        "wait_ms": 0,
        "envelope": env,
        "used": {"calls": calls, "tokens": tokens, "usd": usd},
        "rates": rates,
        "request_usd_est": req_usd,
    }


def check_limits(
    provider_id: str,
    *,
    tokens_est: int = 0,
    chars_est: int = 0,
    op: str = "call",
    consumer: str = "",
    tool_calls_est: int = 0,
    usd_est: float = 0.0,
) -> dict[str, Any]:
    """
    Return {allowed, reason?, remaining_calls, remaining_tokens, wait_ms, remaining_usd}.

    Does not record usage — call after success via record_usage.
    When ``consumer`` is set, also enforces consumer_envelopes + agent protection.
    """
    cfg = load_config()
    if not bool(cfg.get("record_usage", True)):
        # limits still apply if provider block exists
        pass

    # Fail-closed if daily ledger unreadable (never treat as empty budget)
    try:
        from tollgate.usage_ledger import is_ledger_corrupt, load_usage

        day = load_usage()
        if is_ledger_corrupt(day):
            return {
                "allowed": False,
                "reason": (
                    "ledger corrupt/unreadable — fail-closed "
                    f"({day.get('_corrupt_reason') or 'fix keys_usage.json'})"
                ),
                "remaining_calls": 0,
                "remaining_tokens": 0,
                "remaining_usd": 0.0,
                "ledger_corrupt": True,
                "soft_warn": False,
                "wait_ms": 0,
            }
    except Exception as e:  # noqa: BLE001
        return {
            "allowed": False,
            "reason": f"ledger unavailable — fail-closed ({e})",
            "remaining_calls": 0,
            "remaining_tokens": 0,
            "remaining_usd": 0.0,
            "ledger_corrupt": True,
            "soft_warn": False,
            "wait_ms": 0,
        }

    # Per-consumer envelope first (lane isolation before provider spend)
    if (consumer or "").strip():
        # L3 scopes before numeric budgets
        sc = check_consumer_scope(
            consumer,
            provider=provider_id,
            op=op,
        )
        if not sc.get("allowed"):
            return sc
        cl = check_consumer_limits(
            consumer,
            tokens_est=tokens_est,
            tool_calls_est=tool_calls_est,
            usd_est=usd_est,
        )
        if not cl.get("allowed"):
            return {
                "allowed": False,
                "reason": cl.get("reason"),
                "remaining_calls": cl.get("remaining_calls"),
                "remaining_tokens": cl.get("remaining_tokens"),
                "remaining_usd": cl.get("remaining_usd"),
                "consumer": cl.get("consumer"),
                "consumer_limits": cl,
                "soft_warn": False,
                "wait_ms": 0,
            }
    else:
        cl = {"allowed": True, "soft_warn": False}

    # Cost guard first (high-risk list + max_usd_day)
    cg = check_cost_guard(provider_id, tokens_est=tokens_est)
    if not cg.get("allowed"):
        return {
            "allowed": False,
            "reason": cg.get("reason"),
            "remaining_calls": 0,
            "remaining_tokens": 0,
            "remaining_usd": cg.get("remaining_usd"),
            "high_risk": cg.get("high_risk"),
            "soft_warn": False,
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

    soft = bool(cg.get("soft_warn")) or bool(cl.get("soft_warn"))
    soft_reason = cg.get("soft_reason") or cl.get("soft_reason")
    return {
        "allowed": True,
        "reason": None,
        "remaining_calls": (max_calls - calls) if max_calls else None,
        "remaining_tokens": (max_tokens - tokens) if max_tokens else None,
        "remaining_chars": (max_chars - chars) if max_chars else None,
        "remaining_usd": cg.get("remaining_usd"),
        "high_risk": cg.get("high_risk"),
        "soft_warn": soft,
        "soft_reason": soft_reason,
        "budget_ratio": cg.get("budget_ratio"),
        "consumer": cl.get("consumer") if (consumer or "").strip() else None,
        "consumer_limits": cl if (consumer or "").strip() else None,
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
