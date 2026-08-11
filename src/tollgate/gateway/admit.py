"""
L4 Admission control — fail closed before HTTP.

Order (industry best practice):
  request class → cost_guard / high-risk → limits → circuit → allow
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tollgate.gateway.circuit import get_circuits
from tollgate.gateway.context import RequestClass, RequestContext
from tollgate.gateway.errors import ErrorClass, PolicyDeny
from tollgate.limits import check_limits


@dataclass
class AdmitDecision:
    allowed: bool
    code: ErrorClass = ErrorClass.OK
    reason: str = ""
    soft_degrade: bool = False  # e.g. force free model
    limits: dict[str, Any] = field(default_factory=dict)
    context: RequestContext | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "code": self.code.value,
            "reason": self.reason,
            "soft_degrade": self.soft_degrade,
            "limits": self.limits,
            "context": self.context.as_dict() if self.context else None,
        }

    def raise_if_denied(self) -> None:
        if not self.allowed:
            raise PolicyDeny(
                self.reason or "admission denied",
                code=self.code,
                extra=self.as_dict(),
            )


def admit(
    provider: str,
    *,
    op: str = "call",
    tokens_est: int = 0,
    chars_est: int = 0,
    model: str = "",
    ctx: RequestContext | None = None,
    skip_circuit: bool = False,
) -> AdmitDecision:
    """
    Pre-admission for a single provider candidate.

    Does not pick among providers — use router after/with admit per candidate.
    """
    ctx = ctx or RequestContext()
    pid = (provider or "").strip().lower()

    # System probes: still respect disabled/high-risk, but mark non-billable
    if ctx.request_class == RequestClass.SYSTEM:
        ctx.billable = False

    # FREE class: never go to high-risk paid providers
    if ctx.request_class == RequestClass.FREE:
        from tollgate.cost import is_high_risk

        if is_high_risk(pid) and not ctx.allow_paid_fallback:
            return AdmitDecision(
                allowed=False,
                code=ErrorClass.POLICY_DENY,
                reason=f"request_class=free cannot use high-risk provider {pid}",
                context=ctx,
            )

    lim = check_limits(
        pid,
        tokens_est=tokens_est,
        chars_est=chars_est,
        op=op,
        consumer=ctx.consumer_id(),
    )
    if not lim.get("allowed"):
        code = ErrorClass.BUDGET_HARD
        reason = str(lim.get("reason") or "limit denied")
        if lim.get("high_risk"):
            code = ErrorClass.POLICY_DENY
            try:
                from tollgate.alerts import maybe_alert

                maybe_alert(
                    "high_risk_block",
                    provider=pid,
                    message=reason,
                    extra={"op": op, "agent": ctx.agent_id},
                )
            except Exception:  # noqa: BLE001
                pass
        else:
            try:
                from tollgate.alerts import maybe_alert

                maybe_alert(
                    "hard_deny",
                    provider=pid,
                    message=reason,
                    extra={"op": op, "agent": ctx.agent_id, "limits": lim},
                )
            except Exception:  # noqa: BLE001
                pass
        return AdmitDecision(
            allowed=False,
            code=code,
            reason=reason,
            limits=lim,
            context=ctx,
        )

    if not skip_circuit:
        circuits = get_circuits()
        if not circuits.allow(pid, model=model):
            reason = f"circuit OPEN for {pid}/{model or '*'}"
            try:
                from tollgate.alerts import maybe_alert

                maybe_alert("circuit_open", provider=pid, message=reason)
            except Exception:  # noqa: BLE001
                pass
            return AdmitDecision(
                allowed=False,
                code=ErrorClass.PROVIDER_DOWN,
                reason=reason,
                limits=lim,
                context=ctx,
            )

    # Soft degrade: config soft_warn + thin remaining calls/usd
    soft = bool(lim.get("soft_warn"))
    soft_reason = str(lim.get("soft_reason") or "")
    rem_usd = lim.get("remaining_usd")
    if rem_usd is not None and float(rem_usd) < 0.25:
        soft = True
        soft_reason = soft_reason or f"remaining_usd={rem_usd}"
    rem_calls = lim.get("remaining_calls")
    if rem_calls is not None and int(rem_calls) < 5:
        soft = True
        soft_reason = soft_reason or f"remaining_calls={rem_calls}"

    if soft:
        try:
            from tollgate.alerts import maybe_alert

            maybe_alert(
                "soft_budget",
                provider=pid,
                message=soft_reason or "soft budget pressure — prefer free/cheaper",
                extra={
                    "op": op,
                    "agent": ctx.agent_id,
                    "remaining_usd": rem_usd,
                    "budget_ratio": lim.get("budget_ratio"),
                },
            )
        except Exception:  # noqa: BLE001
            pass

    return AdmitDecision(
        allowed=True,
        code=ErrorClass.BUDGET_SOFT if soft else ErrorClass.OK,
        reason="ok" if not soft else (soft_reason or "soft budget pressure — prefer free/cheaper"),
        soft_degrade=soft,
        limits=lim,
        context=ctx,
    )
