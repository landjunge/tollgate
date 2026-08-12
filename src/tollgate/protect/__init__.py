"""
Protect axis — may this request run?

Facade over freeze / admit / limits / short-window rates.
Does not select providers (that is Route).
"""

from __future__ import annotations

from tollgate.gateway.admit import AdmitDecision, admit
from tollgate.gateway.context import RequestContext
from tollgate.gateway.decision import Decision, from_admit_decision
from tollgate.limits import (
    check_consumer_limits,
    check_consumer_scope,
    check_limits,
    consumer_envelope,
)
from tollgate.protect.free_policy import FreePolicy, admit_free_gate, resolve as resolve_free
from tollgate.protect.package_deny import package_deny, package_deny_from_admit
from tollgate.protect.rates import estimate_request_usd, peek_rates, record_rates

__all__ = [
    "AdmitDecision",
    "Decision",
    "FreePolicy",
    "admit",
    "admit_free_gate",
    "check_consumer_limits",
    "check_consumer_scope",
    "check_limits",
    "consumer_envelope",
    "estimate_request_usd",
    "evaluate_protect",
    "from_admit_decision",
    "package_deny",
    "package_deny_from_admit",
    "peek_rates",
    "record_rates",
    "resolve_free",
]


def evaluate_protect(
    provider: str,
    *,
    op: str = "call",
    tokens_est: int = 0,
    chars_est: int = 0,
    model: str = "",
    ctx: RequestContext | None = None,
    skip_circuit: bool = False,
) -> Decision:
    """Run L4 admission and map to Decision."""
    decision = admit(
        provider,
        op=op,
        tokens_est=tokens_est,
        chars_est=chars_est,
        model=model,
        ctx=ctx,
        skip_circuit=skip_circuit,
    )
    return from_admit_decision(decision, provider=provider, op=op)
