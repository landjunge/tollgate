"""
Unified protect deny packaging (Phase 2 + 6).

gateway_call and chat_stream must return the same core deny shape:
  ok, error, error_class, protection, admit, blocked, message
"""

from __future__ import annotations

from typing import Any

from tollgate.consumers import normalize_consumer_id
from tollgate.gateway.decision import Decision
from tollgate.gateway.errors import ErrorClass
from tollgate.redact import redact_secrets


def package_deny(
    *,
    provider: str,
    op: str,
    reason: str,
    code: ErrorClass | str = ErrorClass.POLICY_DENY,
    consumer: str = "",
    protection: str | None = None,
    admit: dict[str, Any] | None = None,
    limits: dict[str, Any] | None = None,
    tokens_est: int = 0,
    tool_calls_est: int = 0,
    audit: bool = True,
    alert: bool = True,
    extra_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Single packaging path for protect denials (audit + alert + block card).

    Used by gateway pipeline and stream dual-path so deny responses match.
    """
    reason = redact_secrets(reason or "denied")
    if isinstance(code, str):
        try:
            code = ErrorClass(code)
        except ValueError:
            code = ErrorClass.POLICY_DENY

    lim = limits if isinstance(limits, dict) else {}
    if admit is not None and not lim:
        ad_lim = admit.get("limits") if isinstance(admit.get("limits"), dict) else {}
        lim = ad_lim if isinstance(ad_lim, dict) else {}

    if protection is None:
        cl = lim.get("consumer_limits") if isinstance(lim.get("consumer_limits"), dict) else {}
        protection = lim.get("protection") or cl.get("protection")

    cid = normalize_consumer_id(consumer) if consumer else ""

    if audit:
        try:
            from tollgate.audit_log import append_audit

            extra = {
                "error_class": code.value if isinstance(code, ErrorClass) else str(code),
                "protection": protection,
            }
            if extra_audit:
                extra.update(extra_audit)
            append_audit(
                "admit_deny",
                provider=provider,
                op=op,
                consumer=cid,
                error=reason,
                ok=False,
                extra=extra,
            )
        except Exception as e:  # noqa: BLE001
            from tollgate.soft_fail import soft_fail

            soft_fail("audit", e, provider=provider, op=op, message="admit_deny audit")

    if alert:
        try:
            from tollgate.alerts import maybe_alert

            if protection or "agent protection" in reason.lower():
                maybe_alert(
                    "agent_protection",
                    provider=provider,
                    message=reason,
                    extra={
                        "consumer": cid,
                        "op": op,
                        "protection": protection,
                    },
                )
        except Exception as e:  # noqa: BLE001
            from tollgate.soft_fail import soft_fail

            soft_fail("alerts", e, provider=provider, op=op)

    blocked = None
    try:
        from tollgate.block_view import build_block_card

        cl = lim.get("consumer_limits") if isinstance(lim.get("consumer_limits"), dict) else {}
        blocked = build_block_card(
            reason=reason,
            consumer=cid,
            provider=provider,
            op=op,
            protection=cl.get("protection") or lim.get("protection") or protection,
            limits=lim,
            tool_calls_est=int(tool_calls_est or 0),
            tokens_est=int(tokens_est or 0),
        )
    except Exception as e:  # noqa: BLE001
        from tollgate.soft_fail import soft_fail

        soft_fail("block_view", e, provider=provider, op=op)
        blocked = None

    d = Decision.deny(
        reason,
        code=code if isinstance(code, ErrorClass) else ErrorClass.POLICY_DENY,
        provider=provider,
        op=op,
        protection=str(protection) if protection else None,
        admit=admit,
        blocked=blocked,
    )
    return d.as_dict()


def package_deny_from_admit(
    decision: Any,
    *,
    provider: str,
    op: str,
    consumer: str = "",
    tokens_est: int = 0,
    tool_calls_est: int = 0,
    extra_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map AdmitDecision → packaged deny dict."""
    reason = str(getattr(decision, "reason", None) or "denied")
    code = getattr(decision, "code", ErrorClass.POLICY_DENY)
    admit_dict = decision.as_dict() if hasattr(decision, "as_dict") else None
    lim = getattr(decision, "limits", None) if hasattr(decision, "limits") else None
    if not isinstance(lim, dict):
        lim = (admit_dict or {}).get("limits") if isinstance(admit_dict, dict) else {}
    return package_deny(
        provider=provider,
        op=op,
        reason=reason,
        code=code,
        consumer=consumer,
        admit=admit_dict if isinstance(admit_dict, dict) else None,
        limits=lim if isinstance(lim, dict) else None,
        tokens_est=tokens_est,
        tool_calls_est=tool_calls_est,
        extra_audit=extra_audit,
    )
