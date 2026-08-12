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


def estimate_tool_calls_est(
    *,
    explicit: int = 0,
    messages: list[Any] | None = None,
    tools: list[Any] | None = None,
    header_val: str | int | None = None,
) -> int:
    """
    Resolve tool-loop depth for Protect (max_tool_calls).

    Priority:
      1. explicit body ``tool_calls_est``
      2. header ``X-Tollgate-Tool-Calls-Est``
      3. infer from message history (role=tool + assistant.tool_calls)
      4. len(tools) only as last resort (schema list — weak signal)

    Agent frameworks that replay tool history get loop protection without
    remembering to set ``tool_calls_est`` on every hop.
    """
    try:
        ex = int(explicit or 0)
    except (TypeError, ValueError):
        ex = 0
    if ex > 0:
        return ex
    if header_val is not None and str(header_val).strip() != "":
        try:
            hv = int(str(header_val).strip())
            if hv > 0:
                return hv
        except (TypeError, ValueError):
            pass
    n = 0
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "")
        if role == "tool":
            n += 1
            continue
        if role == "assistant":
            tc = m.get("tool_calls")
            if isinstance(tc, list):
                n += len(tc)
            elif isinstance(tc, dict):
                n += 1
            # function_call (legacy single)
            if m.get("function_call"):
                n += 1
    if n > 0:
        return n
    if isinstance(tools, list) and tools:
        return len(tools)
    return 0


def openai_error(
    message: str,
    *,
    status: int = 400,
    err_type: str = "invalid_request_error",
    code: str | None = None,
    tollgate: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    body: dict[str, Any] = {
        "error": {
            "message": message,
            "type": err_type,
            "param": None,
            "code": code,
        }
    }
    if tollgate:
        body["error"]["tollgate"] = tollgate
    return body, status


def _tollgate_error_meta(result: dict[str, Any]) -> dict[str, Any]:
    """Ops metadata for clients (no secrets) — protection field, wait, class."""
    admit = result.get("admit") if isinstance(result.get("admit"), dict) else {}
    limits = admit.get("limits") if isinstance(admit.get("limits"), dict) else {}
    if not limits and isinstance(result.get("limits"), dict):
        limits = result["limits"]
    wait_ms = int(
        limits.get("wait_ms")
        or result.get("wait_ms")
        or 0
    )
    meta: dict[str, Any] = {
        "error_class": str(
            result.get("error_class") or admit.get("code") or ""
        )
        or None,
        "protection": limits.get("protection") or result.get("protection"),
        "provider": result.get("provider") or admit.get("provider"),
        "consumer": (
            (admit.get("context") or {}).get("consumer")
            if isinstance(admit.get("context"), dict)
            else result.get("consumer")
        ),
        "wait_ms": wait_ms if wait_ms > 0 else None,
        "retry_after_s": max(1, int(wait_ms / 1000)) if wait_ms > 0 else None,
    }
    # Product Aha card (Protect)
    blocked = result.get("blocked")
    if isinstance(blocked, dict):
        meta["blocked"] = blocked
        if blocked.get("message"):
            meta["message"] = blocked["message"]
    # drop Nones for compact payloads
    return {k: v for k, v in meta.items() if v is not None and v != ""}


def map_tollgate_error(
    result: dict[str, Any],
) -> tuple[dict[str, Any], int, dict[str, str]]:
    """
    Map Tollgate deny/upstream failure → OpenAI-shaped error + HTTP status + headers.

    Returns ``(body, status_code, headers)``. Headers may include ``Retry-After``.
    """
    err = str(result.get("error") or "request failed")
    ec = str(result.get("error_class") or result.get("admit", {}).get("code") or "")
    low = err.lower()
    meta = _tollgate_error_meta(result)
    # Prefer human operator English for the public error.message
    blocked = result.get("blocked") if isinstance(result.get("blocked"), dict) else {}
    human = str(blocked.get("human") or meta.get("message") or "").strip()
    if not human and meta.get("protection"):
        try:
            from tollgate.block_view import human_block_sentence

            human = human_block_sentence(
                prot=str(meta.get("protection") or ""),
                consumer=str(meta.get("consumer") or ""),
                reason=err,
            )
        except Exception:  # noqa: BLE001
            human = ""
    if "circuit" in low or ec == "PROVIDER_DOWN":
        human = human or (
            "A provider is unavailable (circuit open or down). "
            "Tollgate will cool down and use a fallback if configured."
        )
    if (
        result.get("failover")
        or result.get("failover_hops")
        or (isinstance(result.get("failover"), dict))
    ):
        # success path headers elsewhere; on error leave human as-is
        pass
    display = human if human else err
    headers: dict[str, str] = {}
    if meta.get("retry_after_s"):
        headers["Retry-After"] = str(int(meta["retry_after_s"]))
    # Always expose class for operators / n8n
    if meta.get("error_class"):
        headers["X-Tollgate-Error-Class"] = str(meta["error_class"])[:64]
    if meta.get("protection"):
        headers["X-Tollgate-Protection"] = str(meta["protection"])[:64]
    if human:
        headers["X-Tollgate-Human"] = human[:200]

    if "auth" in low or (ec in ("AUTH_DEAD", "POLICY_DENY") and "key" in low):
        body, status = openai_error(
            display,
            status=401,
            err_type="invalid_request_error",
            code="invalid_api_key",
            tollgate=meta,
        )
        return body, status, headers
    if (
        "rate" in low
        or ec == "RATE_LIMIT"
        or "429" in low
        or "max_requests_minute" in low
        or meta.get("protection") == "max_requests_minute"
    ):
        body, status = openai_error(
            display
            or "Rate limit exceeded for this agent. Wait a moment or raise max_requests_minute.",
            status=429,
            err_type="rate_limit_error",
            code="rate_limit_exceeded",
            tollgate=meta,
        )
        if "Retry-After" not in headers:
            headers["Retry-After"] = "1"
        return body, status, headers
    if (
        "budget" in low
        or "limit" in low
        or "agent protection" in low
        or ec in ("BUDGET_HARD", "POLICY_DENY")
        or meta.get("protection")
    ):
        body, status = openai_error(
            display or err,
            status=402,
            err_type="insufficient_quota",
            code="insufficient_quota",
            tollgate=meta,
        )
        return body, status, headers
    if "circuit" in low or ec == "PROVIDER_DOWN":
        body, status = openai_error(
            display
            or "Provider unavailable. Configure a fallback and run Prove when ready.",
            status=503,
            err_type="server_error",
            code="provider_down",
            tollgate=meta,
        )
        return body, status, headers
    body, status = openai_error(
        display or err,
        status=502,
        err_type="server_error",
        code=ec or "upstream_error",
        tollgate=meta,
    )
    return body, status, headers


def response_headers(
    result: dict[str, Any],
    *,
    consumer: str = "",
    requested_model: str = "",
) -> dict[str, str]:
    """Ops headers for successful (and some error) responses."""
    headers: dict[str, str] = {}
    prov = str(result.get("provider") or "").strip()
    mid = str(result.get("model") or "").strip()
    req = (requested_model or "").strip()
    if consumer:
        headers["X-Tollgate-Consumer"] = consumer[:64]
    if prov:
        headers["X-Tollgate-Provider"] = prov[:64]
    if mid:
        headers["X-Tollgate-Model"] = mid[:128]
    if req and mid and req != mid:
        headers["X-Tollgate-Routed-From"] = req[:128]
        headers["X-Tollgate-Routed-To"] = mid[:128]
    if result.get("cache_hit"):
        headers["X-Tollgate-Cache"] = "hit"
    if result.get("soft_degrade"):
        headers["X-Tollgate-Soft-Degrade"] = "1"
    fo = result.get("failover")
    if isinstance(fo, dict) and fo.get("hops"):
        headers["X-Tollgate-Failover-Hops"] = str(int(fo.get("hops") or 0))
        # Human hint: primary failed over
        from_p = str(fo.get("from") or fo.get("primary") or "").strip()
        to_p = str(fo.get("to") or fo.get("used") or prov or "").strip()
        if from_p and to_p and from_p != to_p:
            headers["X-Tollgate-Human"] = (
                f"{from_p} was unavailable. Tollgate switched this request to {to_p}."
            )[:200]
        elif int(fo.get("hops") or 0) > 1:
            headers["X-Tollgate-Human"] = (
                "Primary provider failed; Tollgate completed this request via failover."
            )
    elif result.get("failover_hops"):
        headers["X-Tollgate-Failover-Hops"] = str(int(result.get("failover_hops") or 0))
        if int(result.get("failover_hops") or 0) > 1:
            headers["X-Tollgate-Human"] = (
                "Primary provider failed; Tollgate completed this request via failover."
            )
    return headers


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
