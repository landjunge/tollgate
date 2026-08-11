"""
Single entry for billable ops — admission + service.call + circuit feedback.

Tools and agents should use this instead of importing provider modules directly.
"""

from __future__ import annotations

from typing import Any

from tollgate.gateway.admit import admit
from tollgate.gateway.circuit import get_circuits
from tollgate.gateway.context import RequestContext, RequestClass
from tollgate.gateway.errors import ErrorClass, PolicyDeny, classify_result
from tollgate.redact import redact_secrets


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
    Admit → KeysService.call → circuit update.

    Always returns a dict with ok / error / admit / error_class.
    """
    from tollgate import get_keys_service

    ctx = ctx or RequestContext()
    mid = model or str(kwargs.get("model") or "")
    decision = admit(
        provider,
        op=op,
        tokens_est=tokens_est,
        chars_est=chars_est,
        model=mid,
        ctx=ctx,
    )
    if not decision.allowed:
        reason = redact_secrets(decision.reason or "denied")
        try:
            from tollgate.audit_log import append_audit

            append_audit(
                "admit_deny",
                provider=provider,
                op=op,
                consumer=ctx.consumer_id(),
                error=reason,
                ok=False,
                extra={"error_class": decision.code.value},
            )
        except Exception:  # noqa: BLE001
            pass
        return {
            "ok": False,
            "error": reason,
            "error_class": decision.code.value,
            "admit": decision.as_dict(),
            "provider": provider,
            "op": op,
        }

    # Operational response cache (not agent memory) — free/batch search & probes only
    cache_key = ""
    try:
        from tollgate.response_cache import cache_eligible, get as cache_get, make_key, put as cache_put

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
                return out
    except Exception:  # noqa: BLE001
        cache_key = ""

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
        return {
            "ok": False,
            "error": err,
            "error_class": e.code.value,
            "admit": decision.as_dict(),
            "provider": provider,
            "op": op,
        }
    except Exception as e:  # noqa: BLE001
        err = redact_secrets(str(e))
        get_circuits().failure(provider, model=mid, message=err)
        return {
            "ok": False,
            "error": err,
            "error_class": ErrorClass.UNKNOWN.value,
            "admit": decision.as_dict(),
            "provider": provider,
            "op": op,
        }

    if not isinstance(result, dict):
        result = {"ok": True, "result": result}

    result.setdefault("admit", decision.as_dict())
    result.setdefault("request", ctx.as_dict())
    result["cache_hit"] = False

    ec = classify_result(result)
    result["error_class"] = ec.value
    circuits = get_circuits()
    if ec == ErrorClass.OK and result.get("ok") is not False:
        circuits.success(provider, model=mid)
        if cache_key:
            try:
                from tollgate.response_cache import put as cache_put

                # store without admit/request to keep cache pure
                to_store = {
                    k: v
                    for k, v in result.items()
                    if k not in ("admit", "request", "cache_hit")
                }
                cache_put(cache_key, to_store)
            except Exception:  # noqa: BLE001
                pass
    elif ec == ErrorClass.AUTH_DEAD:
        circuits.failure(
            provider, model=mid, message=redact_secrets(str(result.get("error"))), hard=True
        )
    elif ec in (ErrorClass.RATE_LIMIT, ErrorClass.PROVIDER_DOWN):
        circuits.failure(
            provider, model=mid, message=redact_secrets(str(result.get("error"))), hard=False
        )
    elif ec == ErrorClass.EDGE_BLOCK:
        circuits.failure(provider, model=mid, message="EDGE_BLOCK", hard=False)

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
