"""Protect short-window rates (re-export surface)."""

from __future__ import annotations

from typing import Any


def record_rates(
    consumer: str,
    *,
    tokens_est: int = 0,
    usd_est: float = 0.0,
) -> dict[str, Any]:
    from tollgate.agent_guard import record_attempt

    return record_attempt(consumer, tokens_est=tokens_est, usd_est=usd_est)


def peek_rates(consumer: str) -> dict[str, Any]:
    from tollgate.agent_guard import peek_rates as _peek

    return _peek(consumer)


def estimate_request_usd(tokens_est: int = 0, *, usd_hint: float = 0.0) -> float:
    from tollgate.agent_guard import estimate_request_usd as _est

    return float(_est(int(tokens_est or 0), usd_hint=usd_hint))
