"""
Unified deny / allow decision for protect path (Phase 2).

Public response shape stays dict-compatible for OpenAI / invoke / gateway_call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tollgate.gateway.errors import ErrorClass


@dataclass
class Decision:
    """Protect/Route decision — one place for deny packaging."""

    allowed: bool
    code: ErrorClass = ErrorClass.OK
    reason: str = ""
    provider: str = ""
    op: str = ""
    protection: str | None = None
    admit: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    blocked: dict[str, Any] | None = None
    soft_degrade: bool = False

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "ok": self.allowed,
            "allowed": self.allowed,
            "error_class": self.code.value,
            "provider": self.provider or None,
            "op": self.op or None,
        }
        if self.allowed:
            out["error"] = None
        else:
            out["error"] = self.reason or "denied"
        if self.protection:
            out["protection"] = self.protection
        if self.admit is not None:
            out["admit"] = self.admit
        if self.blocked:
            out["blocked"] = self.blocked
            out["message"] = self.blocked.get("message") or self.reason
        if self.soft_degrade:
            out["soft_degrade"] = True
        if self.extra:
            for k, v in self.extra.items():
                out.setdefault(k, v)
        return out

    @classmethod
    def allow(cls, *, admit: dict[str, Any] | None = None, soft_degrade: bool = False) -> Decision:
        return cls(
            allowed=True,
            code=ErrorClass.BUDGET_SOFT if soft_degrade else ErrorClass.OK,
            admit=admit,
            soft_degrade=soft_degrade,
        )

    @classmethod
    def deny(
        cls,
        reason: str,
        *,
        code: ErrorClass = ErrorClass.POLICY_DENY,
        provider: str = "",
        op: str = "",
        protection: str | None = None,
        admit: dict[str, Any] | None = None,
        blocked: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Decision:
        return cls(
            allowed=False,
            code=code,
            reason=reason,
            provider=provider,
            op=op,
            protection=protection,
            admit=admit,
            blocked=blocked,
            extra=dict(extra or {}),
        )


def from_admit_decision(
    decision: Any,
    *,
    provider: str = "",
    op: str = "",
) -> Decision:
    """Map AdmitDecision → Decision."""
    if decision is None:
        return Decision.deny("admission denied", provider=provider, op=op)
    allowed = bool(getattr(decision, "allowed", False))
    code = getattr(decision, "code", ErrorClass.POLICY_DENY)
    if not isinstance(code, ErrorClass):
        try:
            code = ErrorClass(str(code))
        except ValueError:
            code = ErrorClass.POLICY_DENY
    reason = str(getattr(decision, "reason", "") or "")
    limits = getattr(decision, "limits", None) or {}
    protection = None
    if isinstance(limits, dict):
        protection = limits.get("protection")
        cl = limits.get("consumer_limits")
        if isinstance(cl, dict) and cl.get("protection"):
            protection = cl.get("protection")
    admit_dict = decision.as_dict() if hasattr(decision, "as_dict") else None
    if allowed:
        return Decision.allow(
            admit=admit_dict,
            soft_degrade=bool(getattr(decision, "soft_degrade", False)),
        )
    return Decision.deny(
        reason or "admission denied",
        code=code,
        provider=provider,
        op=op,
        protection=str(protection) if protection else None,
        admit=admit_dict,
    )
