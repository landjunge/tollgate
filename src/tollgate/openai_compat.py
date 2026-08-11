"""
OpenAI-compatible facade — drop-in base_url for clients that speak OpenAI format.

Does NOT store chat memory. All spend goes through routed_chat / gateway admit.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Iterator


def parse_bearer(authorization: str | None) -> str | None:
    """Return token from ``Authorization: Bearer …`` or None."""
    if not authorization:
        return None
    parts = authorization.strip().split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip() or None
    return authorization.strip() or None


def resolve_intent(model: str, *, prefer_free: bool | None = None) -> tuple[str, bool]:
    """
    Map model id → (intent, prefer_free).

    Conventions:
      free:… / *:free / *free* → free_llm
      tollgate/free → free_llm
      default → llm
    """
    m = (model or "").strip().lower()
    if prefer_free is True:
        return "free_llm", True
    if m in ("", "auto", "tollgate", "tollgate/default"):
        return "llm", False
    if m in ("tollgate/free", "free", "auto-free") or m.startswith("free:"):
        return "free_llm", True
    if m.endswith(":free") or "-free" in m or m.endswith("/free"):
        return "free_llm", True
    return "llm", False


def normalize_messages(messages: list[Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "user")
        content = m.get("content")
        if isinstance(content, list):
            # multimodal: join text parts only
            parts = []
            for p in content:
                if isinstance(p, dict) and p.get("type") == "text":
                    parts.append(str(p.get("text") or ""))
                elif isinstance(p, str):
                    parts.append(p)
            content = "\n".join(parts)
        out.append({"role": role, "content": str(content or "")})
    return out


def openai_error(
    message: str,
    *,
    status: int = 400,
    err_type: str = "invalid_request_error",
    code: str | None = None,
) -> tuple[dict[str, Any], int]:
    body = {
        "error": {
            "message": message,
            "type": err_type,
            "param": None,
            "code": code,
        }
    }
    return body, status


def map_tollgate_error(result: dict[str, Any]) -> tuple[dict[str, Any], int]:
    err = str(result.get("error") or "request failed")
    ec = str(result.get("error_class") or result.get("admit", {}).get("code") or "")
    low = err.lower()
    if "auth" in low or ec in ("AUTH_DEAD", "POLICY_DENY") and "key" in low:
        return openai_error(err, status=401, err_type="invalid_request_error", code="invalid_api_key")
    if "rate" in low or ec == "RATE_LIMIT" or "429" in low:
        return openai_error(err, status=429, err_type="rate_limit_error", code="rate_limit_exceeded")
    if "budget" in low or "limit" in low or ec in ("BUDGET_HARD", "POLICY_DENY"):
        return openai_error(err, status=402, err_type="insufficient_quota", code="insufficient_quota")
    if "circuit" in low or ec == "PROVIDER_DOWN":
        return openai_error(err, status=503, err_type="server_error", code="provider_down")
    return openai_error(err, status=502, err_type="server_error", code=ec or "upstream_error")


def to_openai_completion(
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
    cid = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    tollgate_extra: dict[str, Any] = {
        "provider": result.get("provider"),
        "consumer": consumer,
        "error_class": result.get("error_class"),
        "cache_hit": result.get("cache_hit"),
        "soft_degrade": result.get("soft_degrade"),
        "admit": (result.get("admit") or {}).get("code")
        if isinstance(result.get("admit"), dict)
        else None,
        "failover": result.get("failover"),
    }
    # Non-silent rewrite of tollgate/* or alias model ids → actual provider model
    if req and req != mid:
        tollgate_extra["routed_from"] = req
        tollgate_extra["routed_to"] = mid
    return {
        "id": cid,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": mid,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
                "logprobs": None,
            }
        ],
        "usage": {
            "prompt_tokens": pt,
            "completion_tokens": ct,
            "total_tokens": pt + ct,
        },
        # Tollgate extensions (clients ignore unknown fields)
        "tollgate": tollgate_extra,
    }


def stream_sse_chunks(completion: dict[str, Any]) -> Iterator[str]:
    """
    Synthetic SSE stream from a full completion (fallback).

    Prefer real upstream streaming via ``chat_stream.start_chat_stream`` when
    the provider supports OpenAI ``stream: true``.
    """
    cid = completion.get("id") or f"chatcmpl-{uuid.uuid4().hex[:24]}"
    model = completion.get("model") or "tollgate"
    content = ""
    try:
        content = str(completion["choices"][0]["message"]["content"] or "")
    except Exception:  # noqa: BLE001
        content = ""
    created = int(completion.get("created") or time.time())

    # role chunk
    yield _sse(
        {
            "id": cid,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": ""},
                    "finish_reason": None,
                }
            ],
        }
    )
    # content in pieces (rough word groups)
    if content:
        step = max(24, len(content) // 8)
        for i in range(0, len(content), step):
            piece = content[i : i + step]
            yield _sse(
                {
                    "id": cid,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": piece},
                            "finish_reason": None,
                        }
                    ],
                }
            )
    yield _sse(
        {
            "id": cid,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "usage": completion.get("usage"),
        }
    )
    yield "data: [DONE]\n\n"


def _sse(obj: dict[str, Any]) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def list_models_openai() -> dict[str, Any]:
    """Build OpenAI-style model list from routing config + free zen models."""
    from tollgate.app_config import load_config
    from tollgate import get_keys_service

    data: list[dict[str, Any]] = []
    seen: set[str] = set()
    now = int(time.time())

    def add(mid: str, *, owned: str = "tollgate") -> None:
        m = (mid or "").strip()
        if not m or m in seen:
            return
        seen.add(m)
        data.append(
            {
                "id": m,
                "object": "model",
                "created": now,
                "owned_by": owned,
            }
        )

    add("tollgate/auto")
    add("tollgate/free")
    cfg = load_config()
    models = (cfg.get("routing") or {}).get("models") or {}
    for v in models.values():
        if isinstance(v, str) and v:
            add(v)
    # free aliases
    add("deepseek-v4-flash-free", owned="opencode_zen")
    try:
        inv = get_keys_service().inventory(live=False)
        for card in inv.get("providers") or []:
            if not isinstance(card, dict):
                continue
            pid = str(card.get("id") or "")
            detail = card.get("detail") if isinstance(card.get("detail"), dict) else {}
            for mid in (detail.get("free_models") or detail.get("models") or [])[:20]:
                if isinstance(mid, str):
                    add(mid, owned=pid or "tollgate")
    except Exception:  # noqa: BLE001
        pass

    return {"object": "list", "data": data}
