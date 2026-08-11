"""
Standalone multi-consumer HTTP surface.

  tollgate serve
  → http://127.0.0.1:8787/docs

Native:
  GET  /v1/health | /v1/auth | /v1/providers | /v1/budget | /v1/usage
  POST /v1/route | /v1/invoke
  GET|POST /v1/config

OpenAI-compatible drop-in:
  GET  /v1/models
  POST /v1/chat/completions
  Authorization: Bearer <consumer_id>:<secret>  (or X-Consumer-Key)
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from tollgate import get_keys_service, routed_chat
from tollgate.consumers import auth_status, verify_consumer
from tollgate.gateway.context import RequestClass, RequestContext
from tollgate.gateway.entry import gateway_call
from tollgate.metrics import render_prometheus
from tollgate.openai_compat import (
    list_models_openai,
    map_tollgate_error,
    normalize_messages,
    openai_error,
    parse_bearer,
    resolve_intent,
    stream_sse_chunks,
    to_openai_completion,
)


def _bootstrap_env() -> None:
    try:
        from tollgate.app_config import load_config
        from tollgate.config_validate import assert_config_or_raise
        from tollgate.paths import data_home, pin_data_home_env, user_dir
        from tollgate.secrets import ensure_env_from_key_txt, load_keys, parse_key_file

        pin_data_home_env()
        ensure_env_from_key_txt()
        load_keys()
        kp = user_dir() / "Key.txt"
        if not kp.is_file():
            kp = data_home() / "User" / "Key.txt"
        if kp.is_file():
            for k, v in parse_key_file(kp.read_text(encoding="utf-8")).items():
                os.environ.setdefault(k, v)
        # Config validation at process start (strict via env)
        cfg = load_config(force=True)
        strict = (os.environ.get("TOLLGATE_STRICT_CONFIG") or "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        assert_config_or_raise(cfg, strict=strict)
    except ValueError:
        raise
    except Exception:  # noqa: BLE001
        pass


_bootstrap_env()

app = FastAPI(
    title="Tollgate",
    version="0.1.4",
    description=(
        "Tollgate — multi-consumer API admission + router. "
        "OpenAI-compatible /v1/chat/completions drop-in. "
        "Budgets, circuits, portable/USB. "
        "https://github.com/landjunge/tollgate"
    ),
)


def _require(
    x_consumer_key: str | None,
    x_consumer_id: str | None = None,
    *,
    need_admin: bool = False,
    authorization: str | None = None,
) -> dict[str, Any]:
    # Bearer takes precedence when X-Consumer-Key empty (OpenAI SDK style)
    key = x_consumer_key
    if not (key or "").strip():
        key = parse_bearer(authorization)
    auth = verify_consumer(key, x_consumer_id, need_admin=need_admin)
    if not auth.get("ok"):
        raise HTTPException(status_code=401, detail=auth.get("error") or "unauthorized")
    return auth


class RouteBody(BaseModel):
    intent: str = "llm"
    tokens_est: int = Field(0, ge=0)
    chars_est: int = Field(0, ge=0)
    prefer_free: bool | None = None
    live: bool = False


class InvokeBody(BaseModel):
    provider: str
    op: str = "status"
    arguments: dict[str, Any] = Field(default_factory=dict)
    tokens_est: int = Field(0, ge=0)
    chars_est: int = Field(0, ge=0)
    model: str = ""
    agent_id: str = ""
    job_id: str = ""
    session_id: str = ""
    request_class: str = "interactive"
    allow_paid_fallback: bool = False


@app.get("/v1/health")
def health() -> dict[str, Any]:
    from tollgate.gateway.circuit import get_circuits
    from tollgate.paths import path_snapshot

    ks = get_keys_service()
    return {
        "ok": True,
        "service": "tollgate",
        "product": "Tollgate",
        "version": "0.1.4",
        "extractable": True,
        "multi_consumer": True,
        "portable": path_snapshot(),
        "auth": auth_status(),
        "app": ks.app_status(),
        "circuits": get_circuits().snapshot()[:30],
        "metrics": "/metrics",
    }


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    """Prometheus text exposition (ledger, circuits, cache, portable)."""
    return PlainTextResponse(
        render_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/v1/auth")
def auth_info() -> dict[str, Any]:
    """Public: whether auth is required (never returns secrets)."""
    st = auth_status()
    return {
        "ok": True,
        "required": st["required"],
        "consumers_n": st["consumers_n"],
        "consumers": st["consumers"],
        "header": "X-Consumer-Key: <id>:<secret>",
    }


@app.get("/v1/providers")
def providers(
    live: bool = Query(False),
    x_consumer_key: str | None = Header(default=None, alias="X-Consumer-Key"),
    x_consumer_id: str | None = Header(default=None, alias="X-Consumer-Id"),
) -> dict[str, Any]:
    auth = _require(x_consumer_key, x_consumer_id)
    out = get_keys_service().inventory(live=live)
    out["consumer"] = auth["consumer"]
    return out


@app.get("/v1/budget")
def budget(
    provider: str = Query(""),
    tokens_est: int = Query(0, ge=0),
    chars_est: int = Query(0, ge=0),
    x_consumer_key: str | None = Header(default=None, alias="X-Consumer-Key"),
    x_consumer_id: str | None = Header(default=None, alias="X-Consumer-Id"),
) -> dict[str, Any]:
    auth = _require(x_consumer_key, x_consumer_id)
    ks = get_keys_service()
    if provider.strip():
        return {
            "ok": True,
            "consumer": auth["consumer"],
            "provider": provider,
            "limits": ks.check_provider_limits(
                provider, tokens_est=tokens_est, chars_est=chars_est
            ),
            "usage": ks.usage(),
        }
    return {
        "ok": True,
        "consumer": auth["consumer"],
        "usage": ks.usage(),
        "config": ks.get_config().get("config", {}).get("cost_guard"),
    }


@app.post("/v1/route")
def route(
    body: RouteBody,
    x_consumer_key: str | None = Header(default=None, alias="X-Consumer-Key"),
    x_consumer_id: str | None = Header(default=None, alias="X-Consumer-Id"),
) -> dict[str, Any]:
    auth = _require(x_consumer_key, x_consumer_id)
    out = get_keys_service().route(
        body.intent,
        tokens_est=body.tokens_est,
        chars_est=body.chars_est,
        live=body.live,
    )
    out["consumer"] = auth["consumer"]
    return out


@app.post("/v1/invoke")
def invoke(
    body: InvokeBody,
    x_consumer_key: str | None = Header(default=None, alias="X-Consumer-Key"),
    x_consumer_id: str | None = Header(default=None, alias="X-Consumer-Id"),
) -> dict[str, Any]:
    """Multi-consumer admit + call + meter."""
    auth = _require(x_consumer_key, x_consumer_id)
    consumer = auth["consumer"]
    try:
        rclass = RequestClass(body.request_class or "interactive")
    except ValueError:
        rclass = RequestClass.INTERACTIVE
    ctx = RequestContext(
        agent_id=body.agent_id or consumer,
        job_id=body.job_id,
        session_id=body.session_id,
        request_class=rclass,
        allow_paid_fallback=body.allow_paid_fallback,
    )
    args = dict(body.arguments or {})
    if body.model and "model" not in args:
        args["model"] = body.model
    out = gateway_call(
        body.provider,
        body.op,
        ctx=ctx,
        tokens_est=body.tokens_est,
        chars_est=body.chars_est,
        model=body.model or str(args.get("model") or ""),
        **args,
    )
    out["consumer"] = consumer
    return out


@app.get("/v1/usage")
def usage(
    x_consumer_key: str | None = Header(default=None, alias="X-Consumer-Key"),
    x_consumer_id: str | None = Header(default=None, alias="X-Consumer-Id"),
) -> dict[str, Any]:
    auth = _require(x_consumer_key, x_consumer_id)
    out = get_keys_service().usage()
    if isinstance(out, dict):
        out = dict(out)
        out["consumer"] = auth["consumer"]
    return out


@app.get("/v1/config")
def config_get(
    x_consumer_key: str | None = Header(default=None, alias="X-Consumer-Key"),
    x_consumer_id: str | None = Header(default=None, alias="X-Consumer-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    """Read keys_app.json policy (admin when auth mode)."""
    auth = _require(x_consumer_key, x_consumer_id, need_admin=True, authorization=authorization)
    out = get_keys_service().get_config()
    out["consumer"] = auth["consumer"]
    out["warning"] = (
        "policy config only (no Key.txt secrets); admin scope when auth enabled"
    )
    return out


@app.post("/v1/config")
def config_patch(
    body: dict[str, Any],
    x_consumer_key: str | None = Header(default=None, alias="X-Consumer-Key"),
    x_consumer_id: str | None = Header(default=None, alias="X-Consumer-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    """Deep-merge patch into keys_app.json (admin when auth mode)."""
    auth = _require(x_consumer_key, x_consumer_id, need_admin=True, authorization=authorization)
    if not isinstance(body, dict) or not body:
        raise HTTPException(status_code=400, detail="JSON object patch required")
    patch = (
        body.get("config")
        if isinstance(body.get("config"), dict) and len(body) == 1
        else body
    )
    if not isinstance(patch, dict):
        raise HTTPException(status_code=400, detail="invalid patch")
    out = get_keys_service().set_config(patch)
    out["consumer"] = auth["consumer"]
    return out


# ── OpenAI-compatible drop-in ─────────────────────────────────────────


class ChatCompletionsBody(BaseModel):
    model: str = "tollgate/auto"
    messages: list[dict[str, Any]] = Field(default_factory=list)
    temperature: float | None = 0.7
    max_tokens: int | None = 1024
    stream: bool = False
    # Tollgate extras (optional; ignored by OpenAI SDKs)
    intent: str | None = None
    provider: str | None = None
    request_class: str | None = None
    prefer_free: bool | None = None
    user: str | None = None  # OpenAI user field → agent_id hint


@app.get("/v1/models")
def openai_models(
    x_consumer_key: str | None = Header(default=None, alias="X-Consumer-Key"),
    x_consumer_id: str | None = Header(default=None, alias="X-Consumer-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    """OpenAI-compatible model list."""
    _require(x_consumer_key, x_consumer_id, authorization=authorization)
    return list_models_openai()


@app.post("/v1/chat/completions")
def openai_chat_completions(
    body: ChatCompletionsBody,
    x_consumer_key: str | None = Header(default=None, alias="X-Consumer-Key"),
    x_consumer_id: str | None = Header(default=None, alias="X-Consumer-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> Any:
    """
    OpenAI-compatible chat completions (admission + route + meter).

    Drop-in::

        export OPENAI_BASE_URL=http://127.0.0.1:8787/v1
        export OPENAI_API_KEY=n8n:secret   # or any label in open mode

    ``stream: true`` returns SSE (synthetic chunks from full completion today).
    """
    auth = _require(x_consumer_key, x_consumer_id, authorization=authorization)
    consumer = auth["consumer"]
    msgs = normalize_messages(body.messages)
    if not msgs:
        err, code = openai_error("messages is required", status=400)
        return JSONResponse(err, status_code=code)

    intent = (body.intent or "").strip()
    prefer_free = body.prefer_free
    if not intent:
        intent, auto_free = resolve_intent(body.model, prefer_free=prefer_free)
        if prefer_free is None:
            prefer_free = auto_free
    else:
        prefer_free = bool(prefer_free) if prefer_free is not None else intent == "free_llm"

    # model may be provider-specific id; empty provider → router picks
    mid = (body.model or "").strip()
    provider = (body.provider or "").strip()
    if mid.startswith("tollgate/"):
        mid = ""  # let router choose
    rclass = (body.request_class or "interactive").strip() or "interactive"
    agent = (body.user or f"openai:{consumer}")[:64]

    result = routed_chat(
        msgs,
        intent=intent or "llm",
        model=mid,
        provider=provider,
        max_tokens=int(body.max_tokens or 1024),
        temperature=float(body.temperature if body.temperature is not None else 0.7),
        agent_id=agent,
        request_class=rclass,
        prefer_free=prefer_free,
    )

    if not result.get("ok"):
        err, code = map_tollgate_error(result)
        return JSONResponse(err, status_code=code)

    completion = to_openai_completion(result, model=body.model or "tollgate", consumer=consumer)
    if body.stream:
        return StreamingResponse(
            stream_sse_chunks(completion),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Tollgate-Consumer": consumer,
            },
        )
    return completion


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "tollgate",
        "product": "Tollgate",
        "docs": "/docs",
        "repo": "https://github.com/landjunge/tollgate",
        "openai_base_url": "/v1",
        "openai": ["/v1/chat/completions", "/v1/models"],
        "vision": "docs/VISION.md",
        "architecture": "docs/ARCHITECTURE.md",
        "mcp": "docs/MCP.md",
        "portable": "docs/PORTABLE.md",
        "cost_limits": "docs/COST_LIMITS.md",
        "metrics": "/metrics",
        "v1": [
            "/v1/health",
            "/v1/auth",
            "/v1/models",
            "/v1/chat/completions",
            "/v1/route",
            "/v1/invoke",
            "/v1/budget",
            "/v1/providers",
            "/v1/usage",
            "/v1/config",
        ],
    }
