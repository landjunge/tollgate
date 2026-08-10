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
        return {
            "ok": False,
            "error": decision.reason,
            "error_class": decision.code.value,
            "admit": decision.as_dict(),
            "provider": provider,
            "op": op,
        }

    ks = get_keys_service()
    # system probes: skip recording billable cost ops if needed — service still records;
    # pass billable flag via meta when we enhance ledger
    try:
        result = ks.call(
            provider,
            op,
            tokens_est=tokens_est,
            chars_est=chars_est,
            **kwargs,
        )
    except PolicyDeny as e:
        return {
            "ok": False,
            "error": str(e),
            "error_class": e.code.value,
            "admit": decision.as_dict(),
            "provider": provider,
            "op": op,
        }
    except Exception as e:  # noqa: BLE001
        get_circuits().failure(provider, model=mid, message=str(e))
        return {
            "ok": False,
            "error": str(e),
            "error_class": ErrorClass.UNKNOWN.value,
            "admit": decision.as_dict(),
            "provider": provider,
            "op": op,
        }

    if not isinstance(result, dict):
        result = {"ok": True, "result": result}

    result.setdefault("admit", decision.as_dict())
    result.setdefault("request", ctx.as_dict())

    ec = classify_result(result)
    result["error_class"] = ec.value
    circuits = get_circuits()
    if ec == ErrorClass.OK and result.get("ok") is not False:
        circuits.success(provider, model=mid)
    elif ec == ErrorClass.AUTH_DEAD:
        circuits.failure(provider, model=mid, message=str(result.get("error")), hard=True)
    elif ec in (ErrorClass.RATE_LIMIT, ErrorClass.PROVIDER_DOWN):
        circuits.failure(provider, model=mid, message=str(result.get("error")), hard=False)
    elif ec == ErrorClass.EDGE_BLOCK:
        # do not burn key circuit the same way — short open on provider only
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
