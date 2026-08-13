"""
Route axis — where should this request run?

Facade over router, failover, circuits. Must not own budget logic.
"""

from __future__ import annotations

from typing import Any

from tollgate.failover import (
    annotate_failure,
    annotate_success,
    auto_failover_enabled,
    build_candidates,
    is_retriable_failure,
)
from tollgate.gateway.circuit import (
    CircuitRegistry,
    circuits_corrupt,
    get_circuits,
    reset_circuits,
)
from tollgate.route.decision import RouteDecision
from tollgate.router import execute_routed, route

__all__ = [
    "CircuitRegistry",
    "RouteDecision",
    "annotate_failure",
    "annotate_success",
    "auto_failover_enabled",
    "build_candidates",
    "circuits_corrupt",
    "execute_routed",
    "get_circuits",
    "is_retriable_failure",
    "record_failure",
    "record_success",
    "reset_circuits",
    "route",
    "select_route",
]


def select_route(
    service: Any,
    intent: str = "llm",
    *,
    tokens_est: int = 0,
    chars_est: int = 0,
    live: bool = False,
    prefer_free: bool | None = None,
) -> dict[str, Any]:
    """Pick provider/model under limits + health (production router)."""
    return route(
        service,
        intent,
        tokens_est=tokens_est,
        chars_est=chars_est,
        live=live,
        prefer_free=prefer_free,
    )


def record_success(provider: str, *, model: str = "", key_ref: str = "") -> None:
    get_circuits().success(provider, model=model, key_ref=key_ref)


def record_failure(
    provider: str,
    *,
    model: str = "",
    key_ref: str = "",
    message: str = "",
    hard: bool = False,
) -> None:
    get_circuits().failure(
        provider, model=model, key_ref=key_ref, message=message, hard=hard
    )
