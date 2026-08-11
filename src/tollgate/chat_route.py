"""Routed chat: intent → provider/model → gateway admit + call."""

from __future__ import annotations

from typing import Any

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

    If provider is empty, uses KeysService.route(intent).
    Always goes through gateway admission + metering.
    ``consumer`` sets the budget envelope lane (falls back to agent_id).
    """
    from tollgate import get_keys_service

    if isinstance(messages, str):
        msgs: list[dict[str, str]] = [{"role": "user", "content": messages}]
    else:
        msgs = list(messages or [])

    est = tokens_est
    if not est:
        est = max(64, sum(len(str(m.get("content") or "")) for m in msgs) // 4 + int(max_tokens or 0))

    pid = (provider or "").strip().lower()
    mid = (model or "").strip()
    if not pid:
        intent_use = intent
        if prefer_free is True and intent in ("llm", "paid_llm"):
            intent_use = "free_llm"
        route = get_keys_service().route(
            intent_use,
            tokens_est=est,
            live=False,
            prefer_free=prefer_free,
        )
        if not route.get("ok"):
            return {
                "ok": False,
                "error": route.get("error") or "no provider for intent",
                "route": route,
            }
        # route() nests primary under "route"; also accept flat provider/model
        primary = route.get("route") if isinstance(route.get("route"), dict) else {}
        pid = str(route.get("provider") or primary.get("provider") or "").strip().lower()
        if not mid:
            mid = str(route.get("model") or primary.get("model") or "").strip()
        if not pid:
            # last resort: first fallback
            fb = route.get("fallbacks") or []
            if fb and isinstance(fb[0], dict):
                pid = str(fb[0].get("provider") or "").strip().lower()
                if not mid:
                    mid = str(fb[0].get("model") or "").strip()
        if not pid:
            return {"ok": False, "error": "router returned empty provider", "route": route}

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
    )
    return gateway_call(
        pid,
        "chat",
        ctx=ctx,
        tokens_est=est,
        model=mid,
        messages=msgs,
        max_tokens=max_tokens,
        temperature=temperature,
    )
