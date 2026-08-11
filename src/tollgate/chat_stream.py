"""
Real token streaming for OpenAI-compatible providers.

Flow: route → admit → upstream SSE (stream:true) → client SSE → meter.

Synthetic fallback remains in openai_compat.stream_sse_chunks when the
provider cannot stream (or TOLLGATE_STREAM_SYNTHETIC=1).
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Iterator

from tollgate.gateway.admit import admit
from tollgate.gateway.circuit import get_circuits
from tollgate.gateway.context import RequestClass, RequestContext
from tollgate.openai_compat import _sse, stream_sse_chunks, to_openai_completion
from tollgate.redact import redact_secrets


def can_upstream_stream(provider: str) -> bool:
    """Providers that speak OpenAI chat.completions + stream:true."""
    return (provider or "").strip().lower() in {
        "deepseek",
        "worker",
        "opencode_zen",
        "openrouter",
    }


def force_synthetic() -> bool:
    return (os.environ.get("TOLLGATE_STREAM_SYNTHETIC") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _build_upstream(
    provider: str,
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
) -> dict[str, Any] | None:
    """Return {url, headers, body, model} or None if not streamable."""
    pid = (provider or "").strip().lower()
    msgs = [
        {"role": str(m.get("role") or "user"), "content": str(m.get("content") or "")[:16000]}
        for m in (messages or [])
        if isinstance(m, dict)
    ]
    if not msgs:
        msgs = [{"role": "user", "content": "hi"}]
    mid = (model or "").strip()
    mt = max(1, min(128_000, int(max_tokens or 1024)))
    temp = float(temperature)
    body_base: dict[str, Any] = {
        "messages": msgs,
        "stream": True,
        "temperature": temp,
        "max_tokens": mt,
    }

    if pid == "deepseek" or pid == "worker":
        from tollgate import deepseek as ds
        from tollgate.secrets import is_usable_api_key

        key = ds.api_key(worker=(pid == "worker"))
        if not is_usable_api_key(key):
            return {"error": f"{'WORKER' if pid == 'worker' else 'DEEPSEEK'}_API_KEY missing"}
        mid = mid or ds.default_model() or "deepseek-v4-flash"
        return {
            "url": f"{ds.BASE}/chat/completions",
            "headers": {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            "body": {
                **body_base,
                "model": mid,
                "stream_options": {"include_usage": True},
            },
            "model": mid,
        }

    if pid == "opencode_zen":
        from tollgate import opencode_zen as zen
        from tollgate.secrets import is_usable_api_key

        key = zen.api_key()
        if not is_usable_api_key(key):
            return {"error": "OPENCODE_API_KEY missing"}
        mid = (mid or "deepseek-v4-flash-free").removeprefix("opencode/")
        return {
            "url": f"{zen.BASE}/chat/completions",
            "headers": zen._headers(),  # noqa: SLF001 — shared UA + auth
            "body": {
                **body_base,
                "model": mid,
                "max_tokens": max(1, min(8192, mt)),
            },
            "model": mid,
        }

    if pid == "openrouter":
        from tollgate import openrouter as orouter

        name, key = orouter.resolve_key()
        if not key:
            return {"error": "no OpenRouter key in env chain"}
        mid = mid or "openrouter/free"
        if orouter.free_only() and ":" in mid and not mid.endswith(":free") and "free" not in mid.lower():
            return {"error": f"OPENROUTER_FREE_ONLY blocks paid model {mid}"}
        return {
            "url": f"{orouter.BASE}/chat/completions",
            "headers": {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/landjunge/tollgate",
                "X-Title": "Tollgate",
            },
            "body": {
                **body_base,
                "model": mid,
                "stream_options": {"include_usage": True},
            },
            "model": mid,
            "env": name,
        }

    return None


def _resolve_route(
    *,
    intent: str,
    model: str,
    provider: str,
    tokens_est: int,
    prefer_free: bool | None,
) -> dict[str, Any]:
    from tollgate import get_keys_service

    pid = (provider or "").strip().lower()
    mid = (model or "").strip()
    if pid:
        return {"ok": True, "provider": pid, "model": mid}

    intent_use = intent
    if prefer_free is True and intent in ("llm", "paid_llm"):
        intent_use = "free_llm"
    route = get_keys_service().route(
        intent_use,
        tokens_est=tokens_est,
        live=False,
        prefer_free=prefer_free,
    )
    if not route.get("ok"):
        return {
            "ok": False,
            "error": route.get("error") or "no provider for intent",
            "route": route,
        }
    primary = route.get("route") if isinstance(route.get("route"), dict) else {}
    pid = str(route.get("provider") or primary.get("provider") or "").strip().lower()
    if not mid:
        mid = str(route.get("model") or primary.get("model") or "").strip()
    if not pid:
        fb = route.get("fallbacks") or []
        if fb and isinstance(fb[0], dict):
            pid = str(fb[0].get("provider") or "").strip().lower()
            if not mid:
                mid = str(fb[0].get("model") or "").strip()
    if not pid:
        return {"ok": False, "error": "router returned empty provider", "route": route}
    return {"ok": True, "provider": pid, "model": mid, "route": route}


def start_chat_stream(
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
    requested_model: str = "",
) -> dict[str, Any]:
    """
    Prepare a streaming chat response.

    Returns::

        {ok: False, error, error_class?, ...}
        {ok: True, mode: "upstream"|"synthetic", stream: Iterator[str],
         provider, model, consumer, ...}
    """
    if isinstance(messages, str):
        msgs: list[dict[str, str]] = [{"role": "user", "content": messages}]
    else:
        msgs = list(messages or [])

    est = tokens_est
    if not est:
        est = max(64, sum(len(str(m.get("content") or "")) for m in msgs) // 4 + int(max_tokens or 0))

    resolved = _resolve_route(
        intent=intent,
        model=model,
        provider=provider,
        tokens_est=est,
        prefer_free=prefer_free,
    )
    if not resolved.get("ok"):
        return resolved

    pid = str(resolved["provider"])
    mid = str(resolved.get("model") or "")
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
    cid = ctx.consumer_id()

    decision = admit(
        pid,
        op="chat",
        tokens_est=est,
        model=mid,
        ctx=ctx,
    )
    if not decision.allowed:
        reason = redact_secrets(decision.reason or "denied")
        try:
            from tollgate.audit_log import append_audit

            append_audit(
                "admit_deny",
                provider=pid,
                op="chat",
                consumer=cid,
                error=reason,
                ok=False,
                extra={"error_class": decision.code.value, "stream": True},
            )
        except Exception:  # noqa: BLE001
            pass
        return {
            "ok": False,
            "error": reason,
            "error_class": decision.code.value,
            "admit": decision.as_dict(),
            "provider": pid,
            "op": "chat",
        }

    # Synthetic path: full completion then fake SSE
    if force_synthetic() or not can_upstream_stream(pid):
        from tollgate.gateway.entry import gateway_call

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
        if not result.get("ok"):
            return result
        completion = to_openai_completion(
            result,
            model=requested_model or mid or "tollgate",
            consumer=cid,
        )
        return {
            "ok": True,
            "mode": "synthetic",
            "provider": pid,
            "model": mid or result.get("model"),
            "consumer": cid,
            "admit": decision.as_dict(),
            "stream": stream_sse_chunks(completion),
        }

    up = _build_upstream(
        pid,
        model=mid,
        messages=msgs,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if not up or up.get("error"):
        # key missing etc. — try non-stream gateway for clear error
        from tollgate.gateway.entry import gateway_call

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
        if not result.get("ok"):
            return result
        completion = to_openai_completion(
            result,
            model=requested_model or mid or "tollgate",
            consumer=cid,
        )
        return {
            "ok": True,
            "mode": "synthetic",
            "provider": pid,
            "model": mid,
            "consumer": cid,
            "stream": stream_sse_chunks(completion),
        }

    mid = str(up.get("model") or mid)
    display_model = requested_model or mid or "tollgate"

    def gen() -> Iterator[str]:
        from tollgate.httputil import iter_sse_json
        from tollgate.usage_ledger import record_usage

        chat_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        created = int(time.time())
        prompt_tokens = 0
        completion_tokens = 0
        content_chars = 0
        saw_content = False
        upstream_err: str | None = None
        finish_reason = "stop"

        # role opener (OpenAI clients expect this)
        yield _sse(
            {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": display_model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": ""},
                        "finish_reason": None,
                    }
                ],
            }
        )

        for ev in iter_sse_json(
            "POST",
            str(up["url"]),
            headers=dict(up.get("headers") or {}),
            body=dict(up.get("body") or {}),
            timeout=120.0,
        ):
            if not ev.get("ok"):
                upstream_err = redact_secrets(str(ev.get("error") or "upstream stream failed"))
                break
            if ev.get("done"):
                break
            data = ev.get("data")
            if not isinstance(data, dict):
                continue
            # usage may be on final chunk (stream_options.include_usage)
            usage = data.get("usage")
            if isinstance(usage, dict):
                prompt_tokens = int(usage.get("prompt_tokens") or prompt_tokens or 0)
                completion_tokens = int(
                    usage.get("completion_tokens") or completion_tokens or 0
                )
            choices = data.get("choices") or []
            delta_content = ""
            fr_local = None
            if choices and isinstance(choices[0], dict):
                fr_local = choices[0].get("finish_reason")
                if fr_local:
                    finish_reason = str(fr_local)
                delta = choices[0].get("delta") or {}
                if isinstance(delta, dict):
                    raw_c = delta.get("content")
                    # Zen / some models stream only reasoning_content; clients need delta.content
                    if raw_c is None or raw_c == "":
                        raw_c = delta.get("reasoning_content")
                    if raw_c is not None and raw_c != "":
                        delta_content = str(raw_c)
            if delta_content:
                saw_content = True
                content_chars += len(delta_content)
            # skip empty role-only / empty-reasoning openers from upstream
            if choices and isinstance(choices[0], dict):
                d0 = choices[0].get("delta") or {}
                if isinstance(d0, dict):
                    only_meta = not delta_content and not fr_local
                    keys = set(d0.keys())
                    if only_meta and keys <= {"role", "content", "reasoning_content"}:
                        # empty content/reasoning openers
                        if not any(
                            (d0.get(k) not in (None, ""))
                            for k in ("content", "reasoning_content")
                            if k in d0
                        ) and (not d0.get("role") or "role" in keys):
                            if d0.get("content") in (None, "") and d0.get(
                                "reasoning_content"
                            ) in (None, ""):
                                continue
            if not choices and not usage:
                continue
            # rewrite id/model; normalize delta to content for OpenAI clients
            if delta_content or fr_local or choices:
                out = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": int(data.get("created") or created),
                    "model": str(data.get("model") or display_model),
                    "choices": [
                        {
                            "index": 0,
                            "delta": (
                                {"content": delta_content} if delta_content else {}
                            ),
                            "finish_reason": fr_local,
                        }
                    ],
                }
                yield _sse(out)

        if upstream_err:
            get_circuits().failure(pid, model=mid, message=upstream_err, hard=False)
            # surface as a short error delta so clients see something
            yield _sse(
                {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": display_model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": f"\n[tollgate stream error: {upstream_err[:120]}]"},
                            "finish_reason": None,
                        }
                    ],
                }
            )
            finish_reason = "stop"
        else:
            get_circuits().success(pid, model=mid)

        if completion_tokens <= 0 and content_chars:
            completion_tokens = max(1, content_chars // 4)
        if prompt_tokens <= 0:
            prompt_tokens = max(1, est // 2)

        # final chunk with usage
        yield _sse(
            {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": display_model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                },
                "tollgate": {
                    "provider": pid,
                    "consumer": cid,
                    "stream_mode": "upstream",
                    "saw_content": saw_content,
                    "soft_degrade": decision.soft_degrade,
                },
            }
        )
        yield "data: [DONE]\n\n"

        # meter after stream (ops only — not agent memory)
        try:
            record_usage(
                pid,
                op="chat",
                tokens_in=prompt_tokens,
                tokens_out=completion_tokens,
                error=bool(upstream_err),
                consumer=cid,
                meta={"model": mid, "stream": True},
            )
        except Exception:  # noqa: BLE001
            pass
        try:
            from tollgate.audit_log import append_audit

            append_audit(
                "usage",
                provider=pid,
                op="chat",
                consumer=cid,
                tokens=prompt_tokens + completion_tokens,
                ok=not upstream_err,
                error=upstream_err or "",
                extra={"stream": True},
            )
        except Exception:  # noqa: BLE001
            pass

    return {
        "ok": True,
        "mode": "upstream",
        "provider": pid,
        "model": mid,
        "consumer": cid,
        "admit": decision.as_dict(),
        "stream": gen(),
    }
