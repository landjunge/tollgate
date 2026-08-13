"""Routed chat: intent → provider/model → gateway admit + call (+ failover)."""

from __future__ import annotations

from typing import Any

from tollgate.failover import (
    annotate_failure,
    annotate_success,
    build_candidates,
    is_retriable_failure,
)
from tollgate.gateway.context import RequestClass, RequestContext
from tollgate.gateway.entry import gateway_call


def routed_chat(
    messages: list[dict[str, str]] | str,
    *,
    intent: str = "llm",
    model: str = "",
    provider: str = "",
    max_tokens: int = 1024,
    temperature: float = 0.7,
    tokens_est: int = 0,
    tool_calls_est: int = 0,
    agent_id: str = "gnom",
    consumer: str = "",
    job_id: str = "",
    session_id: str = "",
    request_class: str = "interactive",
    allow_paid_fallback: bool = False,
    prefer_free: bool | None = None,
) -> dict[str, Any]:
    """
    High-level multi-consumer chat.

    If provider is empty, uses KeysService.route(intent) and — when
    ``auto_failover`` is on — retries fallbacks on retriable provider errors.
    Explicit ``provider=`` pins a single hop (no failover).
    """
    if isinstance(messages, str):
        msgs: list[dict[str, str]] = [{"role": "user", "content": messages}]
    else:
        msgs = list(messages or [])

    # L3 consumer intent scope (before provider pick)
    cid_hint = (consumer or agent_id or "").strip()
    if cid_hint:
        try:
            from tollgate.limits import check_consumer_scope

            sc = check_consumer_scope(cid_hint, intent=intent)
            if not sc.get("allowed"):
                return {
                    "ok": False,
                    "error": sc.get("reason") or "scope denied",
                    "error_class": "POLICY_DENY",
                    "protection": "scope",
                    "consumer": cid_hint,
                }
        except Exception as e:  # noqa: BLE001
            return {
                "ok": False,
                "error": f"scope check failed — fail-closed ({e})",
                "error_class": "POLICY_DENY",
                "protection": "scope",
                "consumer": cid_hint,
            }

    est = tokens_est
    if not est:
        est = max(64, sum(len(str(m.get("content") or "")) for m in msgs) // 4 + int(max_tokens or 0))

    built = build_candidates(
        provider=provider,
        model=model,
        intent=intent,
        tokens_est=est,
        prefer_free=prefer_free,
    )
    if not built.get("ok"):
        return {
            "ok": False,
            "error": built.get("error") or "no provider for intent",
            "route": built.get("route"),
        }

    try:
        rclass = RequestClass(request_class or "interactive")
    except ValueError:
        rclass = RequestClass.INTERACTIVE

    ctx = RequestContext(
        agent_id=agent_id,
        consumer=(consumer or agent_id or "")[:64],
        job_id=job_id,
        session_id=session_id,
        request_class=rclass,
        allow_paid_fallback=allow_paid_fallback,
        tool_calls_est=max(0, int(tool_calls_est or 0)),
    )

    tried: list[dict[str, Any]] = []
    last: dict[str, Any] | None = None

    for cand in built["candidates"]:
        pid = str(cand.get("provider") or "").strip().lower()
        mid = str(cand.get("model") or "").strip()
        if not pid:
            continue
        result = gateway_call(
            pid,
            "chat",
            ctx=ctx,
            tokens_est=est,
            model=mid,
            messages=msgs,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        hop = {
            "provider": pid,
            "model": mid,
            "ok": bool(result.get("ok")),
            "error": result.get("error"),
            "error_class": result.get("error_class"),
        }
        tried.append(hop)
        last = result

        if result.get("ok") and str(result.get("content") or "").strip():
            return annotate_success(result, tried=tried, provider=pid, model=mid)

        # empty completion: treat as fail + maybe hop
        if result.get("ok") and not str(result.get("content") or "").strip():
            hop["ok"] = False
            hop["error"] = hop.get("error") or "empty completion"
            hop["error_class"] = "EMPTY_COMPLETION"
            last = {
                **result,
                "ok": False,
                "error": "empty completion",
                "error_class": "EMPTY_COMPLETION",
            }

        if not is_retriable_failure(last):
            return annotate_failure(last, tried=tried)

        # else: try next candidate

    return annotate_failure(last, tried=tried)
