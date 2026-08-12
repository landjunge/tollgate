"""
Single entry for billable ops — modular pipeline (Protect → Execute → Route feedback).

Tools and agents should use this instead of importing provider modules directly.

Pipeline stages (Phase 1+):
  prove availability → protect admit → protect rates → cache → execute → circuit → cache store
"""

from __future__ import annotations

from typing import Any

from tollgate.gateway.admit import AdmitDecision, admit
from tollgate.gateway.circuit import get_circuits
from tollgate.gateway.context import RequestClass, RequestContext
from tollgate.gateway.errors import ErrorClass, PolicyDeny, classify_result
from tollgate.redact import redact_secrets


# ── Stage helpers (named pipeline — no public API break) ─────────────


def _stage_prove_availability(
    provider: str,
    *,
    op: str,
    ctx: RequestContext,
) -> dict[str, Any] | None:
    """
    Prove gate: chaos inject / gradual recovery.
    Returns deny dict or None if available.
    """
    from tollgate.prove.availability import check_provider_available

    av = check_provider_available(provider)
    if av.available:
        return None
    deny = av.as_deny_dict(provider=provider, op=op)
    if av.subsystem_error:
        try:
            from tollgate.audit_log import append_audit

            append_audit(
                "protection_error",
                provider=provider,
                op=op,
                consumer=ctx.consumer_id(),
                error=deny.get("error") or "chaos check failed",
                ok=False,
                extra={"subsystem": "chaos", "fail_closed": True},
            )
        except Exception as e:  # noqa: BLE001
            from tollgate.soft_fail import soft_fail

            soft_fail("audit", e, provider=provider, op=op, message="protection_error audit")
    return deny


def _build_deny_response(
    *,
    provider: str,
    op: str,
    ctx: RequestContext,
    decision: AdmitDecision | None,
    reason: str,
    code: ErrorClass,
    tokens_est: int = 0,
    protection: str | None = None,
    admit_dict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Single packaging path for protect denials (delegates to protect.package_deny)."""
    from tollgate.protect.package_deny import package_deny, package_deny_from_admit

    if decision is not None:
        return package_deny_from_admit(
            decision,
            provider=provider,
            op=op,
            consumer=ctx.consumer_id(),
            tokens_est=tokens_est,
            tool_calls_est=int(getattr(ctx, "tool_calls_est", 0) or 0),
        )
    return package_deny(
        provider=provider,
        op=op,
        reason=reason,
        code=code,
        consumer=ctx.consumer_id(),
        protection=protection,
        admit=admit_dict,
        tokens_est=tokens_est,
        tool_calls_est=int(getattr(ctx, "tool_calls_est", 0) or 0),
    )


def _stage_protect_admit(
    provider: str,
    *,
    op: str,
    tokens_est: int,
    chars_est: int,
    model: str,
    ctx: RequestContext,
) -> tuple[AdmitDecision | None, dict[str, Any] | None]:
    """
    Protect: L4 admission.
    Returns (admit_decision, None) on allow, or (None, deny_dict) on deny.
    """
    decision = admit(
        provider,
        op=op,
        tokens_est=tokens_est,
        chars_est=chars_est,
        model=model,
        ctx=ctx,
    )
    if decision.allowed:
        return decision, None
    deny = _build_deny_response(
        provider=provider,
        op=op,
        ctx=ctx,
        decision=decision,
        reason=decision.reason or "denied",
        code=decision.code,
        tokens_est=tokens_est,
    )
    return None, deny


def _stage_protect_rates(
    provider: str,
    *,
    op: str,
    ctx: RequestContext,
    decision: AdmitDecision,
    tokens_est: int,
) -> dict[str, Any] | None:
    """Protect: short-window rates after admit. Returns deny dict or None."""
    try:
        from tollgate.protect import estimate_request_usd, package_deny, record_rates

        ra = record_rates(
            ctx.consumer_id(),
            tokens_est=tokens_est,
            usd_est=float(
                (decision.limits or {}).get("request_usd_est")
                or estimate_request_usd(tokens_est)
            ),
        )
        if isinstance(ra, dict) and ra.get("ok") is False and ra.get("corrupt"):
            return package_deny(
                provider=provider,
                op=op,
                reason=str(ra.get("error") or "agent_rates corrupt — fail-closed"),
                code=ErrorClass.BUDGET_HARD,
                consumer=ctx.consumer_id(),
                protection="agent_rates",
                admit=decision.as_dict(),
                tokens_est=tokens_est,
                tool_calls_est=int(getattr(ctx, "tool_calls_est", 0) or 0),
            )
    except Exception as e:  # noqa: BLE001
        # rates stage is best-effort except corrupt→fail-closed above
        from tollgate.soft_fail import soft_fail

        soft_fail("agent_rates", e, provider=provider, op=op)
    return None


def _stage_cache_lookup(
    provider: str,
    op: str,
    ctx: RequestContext,
    decision: AdmitDecision,
    kwargs: dict[str, Any],
) -> tuple[str, dict[str, Any] | None]:
    """Returns (cache_key, hit_result_or_None)."""
    cache_key = ""
    try:
        from tollgate.response_cache import (
            cache_eligible,
            get as cache_get,
            make_key,
        )

        if cache_eligible(provider, op, ctx=ctx):
            consumer = ctx.consumer_id()
            cache_key = make_key(provider, op, kwargs, consumer=consumer)
            hit = cache_get(cache_key)
            if hit is not None:
                out = dict(hit)
                out["cache_hit"] = True
                out.setdefault("admit", decision.as_dict())
                out.setdefault("request", ctx.as_dict())
                if decision.soft_degrade:
                    out["soft_degrade"] = True
                    out["soft_degrade_reason"] = decision.reason
                return cache_key, out
    except Exception as e:  # noqa: BLE001
        from tollgate.soft_fail import soft_fail

        soft_fail("response_cache", e, provider=provider, op=op)
        cache_key = ""
    return cache_key, None


def _stage_execute(
    provider: str,
    op: str,
    *,
    ctx: RequestContext,
    decision: AdmitDecision,
    tokens_est: int,
    chars_est: int,
    model: str,
    kwargs: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """
    Provider execute via KeysService.

    Returns (result, skip_circuit_feedback).
    skip_circuit_feedback=True when PolicyDeny (no circuit) or exception
    already recorded a circuit failure.
    """
    from tollgate import get_keys_service

    ks = get_keys_service()
    try:
        result = ks.call(
            provider,
            op,
            tokens_est=tokens_est,
            chars_est=chars_est,
            consumer=ctx.consumer_id(),
            **kwargs,
        )
    except PolicyDeny as e:
        err = redact_secrets(str(e))
        return (
            {
                "ok": False,
                "error": err,
                "error_class": e.code.value,
                "admit": decision.as_dict(),
                "provider": provider,
                "op": op,
            },
            True,
        )
    except Exception as e:  # noqa: BLE001
        err = redact_secrets(str(e))
        get_circuits().failure(provider, model=model, message=err)
        return (
            {
                "ok": False,
                "error": err,
                "error_class": ErrorClass.UNKNOWN.value,
                "admit": decision.as_dict(),
                "provider": provider,
                "op": op,
            },
            True,
        )

    if not isinstance(result, dict):
        result = {"ok": True, "result": result}
    result.setdefault("admit", decision.as_dict())
    result.setdefault("request", ctx.as_dict())
    result["cache_hit"] = False
    return result, False


def _stage_route_feedback(
    provider: str,
    *,
    model: str,
    result: dict[str, Any],
    cache_key: str = "",
) -> dict[str, Any]:
    """Route axis: circuit success/failure + optional cache store."""
    ec = classify_result(result)
    result["error_class"] = ec.value
    circuits = get_circuits()
    if ec == ErrorClass.OK and result.get("ok") is not False:
        circuits.success(provider, model=model)
        if cache_key:
            try:
                from tollgate.response_cache import put as cache_put

                to_store = {
                    k: v
                    for k, v in result.items()
                    if k not in ("admit", "request", "cache_hit")
                }
                cache_put(cache_key, to_store)
            except Exception as e:  # noqa: BLE001
                from tollgate.soft_fail import soft_fail

                soft_fail("response_cache", e, provider=provider, op="cache_put")
    elif ec == ErrorClass.AUTH_DEAD:
        circuits.failure(
            provider,
            model=model,
            message=redact_secrets(str(result.get("error"))),
            hard=True,
        )
    elif ec in (ErrorClass.RATE_LIMIT, ErrorClass.PROVIDER_DOWN):
        circuits.failure(
            provider,
            model=model,
            message=redact_secrets(str(result.get("error"))),
            hard=False,
        )
    elif ec == ErrorClass.EDGE_BLOCK:
        circuits.failure(provider, model=model, message="EDGE_BLOCK", hard=False)
    return result


# ── Public API ───────────────────────────────────────────────────────


def gateway_call(
    provider: str,
    op: str,
    *,
    ctx: RequestContext | None = None,
    tokens_est: int = 0,
    chars_est: int = 0,
    model: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Pipeline: Prove availability → Protect → Execute → Route feedback.

    Always returns a dict with ok / error / admit / error_class.
    """
    ctx = ctx or RequestContext()
    mid = model or str(kwargs.get("model") or "")

    # 1) Prove
    diverted = _stage_prove_availability(provider, op=op, ctx=ctx)
    if diverted is not None:
        return diverted

    # 2) Protect admit
    decision, deny = _stage_protect_admit(
        provider,
        op=op,
        tokens_est=tokens_est,
        chars_est=chars_est,
        model=mid,
        ctx=ctx,
    )
    if deny is not None:
        return deny
    assert decision is not None

    # 3) Protect rates
    rates_deny = _stage_protect_rates(
        provider, op=op, ctx=ctx, decision=decision, tokens_est=tokens_est
    )
    if rates_deny is not None:
        return rates_deny

    # 4) Cache lookup
    cache_key, hit = _stage_cache_lookup(provider, op, ctx, decision, kwargs)
    if hit is not None:
        return hit

    # 5) Execute
    result, skip_circuit = _stage_execute(
        provider,
        op,
        ctx=ctx,
        decision=decision,
        tokens_est=tokens_est,
        chars_est=chars_est,
        model=mid,
        kwargs=kwargs,
    )

    # 6) Route feedback (circuit + cache store) — unless execute already handled it
    if not skip_circuit:
        result = _stage_route_feedback(
            provider, model=mid, result=result, cache_key=cache_key
        )

    if decision.soft_degrade:
        result["soft_degrade"] = True
        result["soft_degrade_reason"] = decision.reason

    return result


def gateway_search(
    query: str,
    *,
    count: int = 5,
    ctx: RequestContext | None = None,
    **kw: Any,
) -> dict[str, Any]:
    return gateway_call(
        "brave",
        "search",
        ctx=ctx or RequestContext(request_class=RequestClass.INTERACTIVE),
        query=query,
        count=count,
        chars_est=0,
        tokens_est=0,
        **kw,
    )
