"""
Anthropic Messages API facade — drop-in for clients that speak Anthropic format.

Does NOT call Anthropic. Routes through Tollgate admit + free/paid LLM providers.
Auth: x-api-key or Authorization Bearer (same consumer secrets as OpenAI surface).
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Iterator

from tollgate.openai_compat import map_tollgate_error


def parse_x_api_key(x_api_key: str | None) -> str | None:
    raw = (x_api_key or "").strip()
    return raw or None


def normalize_anthropic_messages(
    messages: list[Any],
    *,
    system: str | list[Any] | None = None,
) -> list[dict[str, str]]:
    """Anthropic messages (+ optional system) → OpenAI-style [{role, content}]."""
    out: list[dict[str, str]] = []
    sys_text = _content_to_text(system)
    if sys_text:
        out.append({"role": "system", "content": sys_text})
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "user")
        if role == "system":
            # rare: system in messages array
            t = _content_to_text(m.get("content"))
            if t:
                out.append({"role": "system", "content": t})
            continue
        if role not in ("user", "assistant"):
            role = "user"
        text = _content_to_text(m.get("content"))
        out.append({"role": role, "content": text})
    return out


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                btype = str(block.get("type") or "")
                if btype in ("text", "") and block.get("text") is not None:
                    parts.append(str(block.get("text") or ""))
                elif btype == "image":
                    parts.append("[image omitted]")
                elif btype == "tool_result":
                    parts.append(str(block.get("content") or block.get("text") or "")[:4000])
                else:
                    # best-effort
                    if block.get("text") is not None:
                        parts.append(str(block.get("text") or ""))
        return "\n".join(p for p in parts if p)
    return str(content)


def anthropic_error(
    message: str,
    *,
    status: int = 400,
    err_type: str = "invalid_request_error",
) -> tuple[dict[str, Any], int]:
    return {
        "type": "error",
        "error": {
            "type": err_type,
            "message": message,
        },
    }, status


def map_anthropic_error(
    result: dict[str, Any],
) -> tuple[dict[str, Any], int, dict[str, str]]:
    """Map Tollgate deny/errors → Anthropic error shape + HTTP status + headers."""
    body, code, headers = map_tollgate_error(result)
    msg = ""
    err_type = "api_error"
    tg_meta = None
    if isinstance(body.get("error"), dict):
        msg = str(body["error"].get("message") or "")
        ot = str(body["error"].get("type") or "")
        tg_meta = body["error"].get("tollgate")
        if ot == "invalid_request_error":
            err_type = "authentication_error" if code == 401 else "invalid_request_error"
        elif ot == "rate_limit_error":
            err_type = "rate_limit_error"
        elif ot == "insufficient_quota":
            err_type = "invalid_request_error"  # Anthropic has no 402 type; keep message
        else:
            err_type = "api_error"
    if not msg:
        msg = str(result.get("error") or "request failed")
    if code == 402:
        err_type = "invalid_request_error"
    out, status = anthropic_error(msg, status=code, err_type=err_type)
    if tg_meta and isinstance(out.get("error"), dict):
        out["error"]["tollgate"] = tg_meta
    return out, status, headers


def to_anthropic_message(
    result: dict[str, Any],
    *,
    model: str,
    consumer: str = "",
    requested_model: str = "",
) -> dict[str, Any]:
    content = str(result.get("content") or "")
    mid = str(result.get("model") or model or "tollgate")
    req = (requested_model or model or "").strip()
    pt = int(result.get("prompt_tokens") or (result.get("usage") or {}).get("prompt_tokens") or 0)
    ct = int(
        result.get("completion_tokens")
        or (result.get("usage") or {}).get("completion_tokens")
        or 0
    )
    if pt == 0 and ct == 0 and content:
        ct = max(1, len(content) // 4)
    msg_id = f"msg_{uuid.uuid4().hex[:24]}"
    tollgate_extra: dict[str, Any] = {
        "provider": result.get("provider"),
        "consumer": consumer,
        "error_class": result.get("error_class"),
        "cache_hit": result.get("cache_hit"),
    }
    # Non-silent: claude-* / tollgate/* may be rewritten to actual provider model
    if req and (req != mid or req.lower().startswith("claude") or req.startswith("tollgate/")):
        tollgate_extra["routed_from"] = req
        tollgate_extra["routed_to"] = mid
        tollgate_extra["note"] = (
            "Model id was resolved by Tollgate router (not a direct Anthropic call). "
            "No Anthropic API key required."
        )
    return {
        "id": msg_id,
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": content}],
        "model": mid,
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": pt,
            "output_tokens": ct,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
        # Tollgate extensions (clients ignore)
        "tollgate": {
            **tollgate_extra,
            "soft_degrade": result.get("soft_degrade"),
        },
    }


def stream_anthropic_from_text(
    text: str,
    *,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    provider: str = "",
    consumer: str = "",
) -> Iterator[str]:
    """Synthetic Anthropic SSE from a full completion text."""
    msg_id = f"msg_{uuid.uuid4().hex[:24]}"
    mid = model or "tollgate"
    content = text or ""
    out_tok = output_tokens or (max(1, len(content) // 4) if content else 0)
    in_tok = input_tokens or max(1, out_tok)

    yield _event(
        "message_start",
        {
            "type": "message_start",
            "message": {
                "id": msg_id,
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": mid,
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {
                    "input_tokens": in_tok,
                    "output_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
            },
        },
    )
    yield _event(
        "content_block_start",
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""},
        },
    )
    if content:
        step = max(24, len(content) // 8)
        for i in range(0, len(content), step):
            piece = content[i : i + step]
            yield _event(
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": piece},
                },
            )
    yield _event("content_block_stop", {"type": "content_block_stop", "index": 0})
    yield _event(
        "message_delta",
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {"output_tokens": out_tok},
        },
    )
    yield _event(
        "message_stop",
        {
            "type": "message_stop",
            "tollgate": {
                "provider": provider,
                "consumer": consumer,
                "stream_mode": "synthetic",
            },
        },
    )


def stream_anthropic_from_openai_sse(
    openai_sse: Iterator[str],
    *,
    model: str,
    provider: str = "",
    consumer: str = "",
    input_tokens_est: int = 0,
) -> Iterator[str]:
    """
    Convert OpenAI chat.completion.chunk SSE lines → Anthropic Messages SSE.

    Used when we already have an upstream OpenAI stream from chat_stream.
    """
    msg_id = f"msg_{uuid.uuid4().hex[:24]}"
    mid = model or "tollgate"
    started = False
    block_started = False
    output_tokens = 0
    content_chars = 0
    in_tok = max(0, int(input_tokens_est or 0))

    def ensure_start() -> Iterator[str]:
        nonlocal started, block_started
        if not started:
            started = True
            yield _event(
                "message_start",
                {
                    "type": "message_start",
                    "message": {
                        "id": msg_id,
                        "type": "message",
                        "role": "assistant",
                        "content": [],
                        "model": mid,
                        "stop_reason": None,
                        "stop_sequence": None,
                        "usage": {
                            "input_tokens": in_tok or 1,
                            "output_tokens": 0,
                            "cache_creation_input_tokens": 0,
                            "cache_read_input_tokens": 0,
                        },
                    },
                },
            )
        if not block_started:
            block_started = True
            yield _event(
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""},
                },
            )

    for line in openai_sse:
        if not line:
            continue
        # OpenAI lines are "data: {...}\n\n" or "data: [DONE]\n\n"
        for raw_line in line.split("\n"):
            raw_line = raw_line.strip()
            if not raw_line.startswith("data:"):
                continue
            payload = raw_line[5:].lstrip()
            if payload == "[DONE]":
                continue
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            usage = obj.get("usage")
            if isinstance(usage, dict):
                if usage.get("prompt_tokens"):
                    in_tok = int(usage.get("prompt_tokens") or in_tok)
                if usage.get("completion_tokens"):
                    output_tokens = int(usage.get("completion_tokens") or output_tokens)
            choices = obj.get("choices") or []
            if not choices:
                continue
            ch0 = choices[0] if isinstance(choices[0], dict) else {}
            delta = ch0.get("delta") or {}
            piece = ""
            if isinstance(delta, dict):
                piece = str(delta.get("content") or "")
            if piece:
                for ev in ensure_start():
                    yield ev
                content_chars += len(piece)
                yield _event(
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": 0,
                        "delta": {"type": "text_delta", "text": piece},
                    },
                )

    if not started:
        for ev in ensure_start():
            yield ev
    if block_started:
        yield _event("content_block_stop", {"type": "content_block_stop", "index": 0})
    if output_tokens <= 0 and content_chars:
        output_tokens = max(1, content_chars // 4)
    yield _event(
        "message_delta",
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {"output_tokens": output_tokens},
        },
    )
    yield _event(
        "message_stop",
        {
            "type": "message_stop",
            "tollgate": {
                "provider": provider,
                "consumer": consumer,
                "stream_mode": "upstream",
            },
        },
    )


def _event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


