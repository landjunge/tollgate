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

Anthropic-compatible drop-in:
  POST /v1/messages
  x-api-key: <consumer_id>:<secret>  (or Authorization Bearer / X-Consumer-Key)
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
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
    version="0.2.7",
    description=(
        "Tollgate — AI reliability & control plane. "
        "Protect · Route · Prove (chaos failover tests). "
        "https://github.com/landjunge/tollgate"
    ),
)


def _require(
    x_consumer_key: str | None,
    x_consumer_id: str | None = None,
    *,
    need_admin: bool = False,
    authorization: str | None = None,
    x_api_key: str | None = None,
) -> dict[str, Any]:
    # Prefer X-Consumer-Key, then Anthropic x-api-key, then Bearer (OpenAI SDK)
    key = x_consumer_key
    if not (key or "").strip():
        key = (x_api_key or "").strip() or None
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
    tool_calls_est: int = Field(
        0,
        ge=0,
        description="Agent loop depth this turn — enforced via max_tool_calls envelope",
    )
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
        "version": "0.2.7",
        "extractable": True,
        "multi_consumer": True,
        "portable": path_snapshot(),
        "auth": auth_status(),
        "app": ks.app_status(),
        "circuits": get_circuits().snapshot()[:30],
        "metrics": "/metrics",
        "control": "/v1/control",
        "dashboard": "/dashboard",
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


@app.get("/v1/control")
def control_plane_view(
    x_consumer_key: str | None = Header(default=None, alias="X-Consumer-Key"),
    x_consumer_id: str | None = Header(default=None, alias="X-Consumer-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    """
    Product control pane: provider health, consumer burn, headline.

    Protect · Route · Prove — not a secret dump.
    """
    auth = _require(x_consumer_key, x_consumer_id, authorization=authorization)
    from tollgate.control_plane import control_snapshot

    out = control_snapshot()
    out["consumer"] = auth["consumer"]
    return out


@app.get("/v1/resilience")
def resilience_view(
    x_consumer_key: str | None = Header(default=None, alias="X-Consumer-Key"),
    x_consumer_id: str | None = Header(default=None, alias="X-Consumer-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    """AI Resilience Score 0–100 + warnings (Prove pillar)."""
    auth = _require(x_consumer_key, x_consumer_id, authorization=authorization)
    from tollgate.resilience import resilience_score

    out = resilience_score()
    out["consumer"] = auth["consumer"]
    return out


@app.get("/v1/chaos")
def chaos_status_http(
    x_consumer_key: str | None = Header(default=None, alias="X-Consumer-Key"),
    x_consumer_id: str | None = Header(default=None, alias="X-Consumer-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    """Active chaos injects + last failover test report."""
    auth = _require(x_consumer_key, x_consumer_id, authorization=authorization)
    from tollgate.chaos import status as chaos_status

    out = chaos_status()
    out["consumer"] = auth["consumer"]
    return out


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page() -> HTMLResponse:
    """Human-readable control plane (no SPA build)."""
    from tollgate.dashboard_html import DASHBOARD_HTML

    return HTMLResponse(DASHBOARD_HTML)


@app.get("/v1/providers")
def providers(
    live: bool = Query(False),
    x_consumer_key: str | None = Header(default=None, alias="X-Consumer-Key"),
    x_consumer_id: str | None = Header(default=None, alias="X-Consumer-Id"),
) -> dict[str, Any]:
    auth = _require(x_consumer_key, x_consumer_id)
    out = get_keys_service().inventory(live=live)
    out["consumer"] = auth["consumer"]
    try:
        from tollgate.control_plane import provider_health

        out["health"] = provider_health()
    except Exception:  # noqa: BLE001
        pass
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
    from tollgate.limits import check_consumer_limits, consumer_envelope
    from tollgate.usage_ledger import consumer_usage

    cid = auth["consumer"]
    c_lim = check_consumer_limits(cid, tokens_est=tokens_est)
    c_used = consumer_usage(cid)
    if provider.strip():
        return {
            "ok": True,
            "consumer": cid,
            "provider": provider,
            "limits": ks.check_provider_limits(
                provider, tokens_est=tokens_est, chars_est=chars_est
            ),
            "consumer_envelope": consumer_envelope(cid),
            "consumer_limits": c_lim,
            "consumer_usage": c_used,
            "usage": ks.usage(),
        }
    return {
        "ok": True,
        "consumer": cid,
        "consumer_envelope": consumer_envelope(cid),
        "consumer_limits": c_lim,
        "consumer_usage": c_used,
        "usage": ks.usage(),
        "config": ks.get_config().get("config", {}).get("cost_guard"),
    }


@app.post("/v1/route")
def route(
    body: RouteBody,
    explain: bool = Query(True, description="Include why-this-provider explainability"),
    x_consumer_key: str | None = Header(default=None, alias="X-Consumer-Key"),
    x_consumer_id: str | None = Header(default=None, alias="X-Consumer-Id"),
) -> dict[str, Any]:
    auth = _require(x_consumer_key, x_consumer_id)
    out = get_keys_service().route(
        body.intent,
        tokens_est=body.tokens_est,
        chars_est=body.chars_est,
        live=body.live,
        prefer_free=body.prefer_free,
    )
    out["consumer"] = auth["consumer"]
    if explain:
        try:
            from tollgate.control_plane import explain_route

            out["explain"] = explain_route(out)
        except Exception as e:  # noqa: BLE001
            out["explain"] = {"ok": False, "error": str(e)}
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
    args = dict(body.arguments or {})
    if body.model and "model" not in args:
        args["model"] = body.model
    # tool_calls_est: explicit body field, or count tools/tool_calls in arguments
    tools_est = int(body.tool_calls_est or 0)
    if tools_est <= 0:
        for key in ("tool_calls", "tools", "tool_calls_est"):
            raw = args.get(key)
            if isinstance(raw, list):
                tools_est = len(raw)
                break
            if isinstance(raw, (int, float)) and key == "tool_calls_est":
                tools_est = int(raw)
                break
    ctx = RequestContext(
        agent_id=body.agent_id or consumer,
        consumer=consumer,
        job_id=body.job_id,
        session_id=body.session_id,
        request_class=rclass,
        allow_paid_fallback=body.allow_paid_fallback,
        tool_calls_est=max(0, tools_est),
    )
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
    if tools_est:
        out["tool_calls_est"] = tools_est
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

    ``stream: true`` returns SSE — real upstream token stream when the provider
    supports it (deepseek / worker / opencode_zen / openrouter); otherwise
    synthetic chunks from a full completion.
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
    max_tok = int(body.max_tokens or 1024)
    temp = float(body.temperature if body.temperature is not None else 0.7)

    if body.stream:
        from tollgate.chat_stream import start_chat_stream

        started = start_chat_stream(
            msgs,
            intent=intent or "llm",
            model=mid,
            provider=provider,
            max_tokens=max_tok,
            temperature=temp,
            agent_id=agent,
            consumer=consumer,
            request_class=rclass,
            prefer_free=prefer_free,
            requested_model=body.model or "tollgate",
        )
        if not started.get("ok"):
            err, code = map_tollgate_error(started)
            return JSONResponse(err, status_code=code)
        headers = {
            "Cache-Control": "no-cache",
            "X-Tollgate-Consumer": consumer,
            "X-Tollgate-Stream": str(started.get("mode") or "upstream"),
            "X-Tollgate-Provider": str(started.get("provider") or ""),
        }
        return StreamingResponse(
            started["stream"],
            media_type="text/event-stream",
            headers=headers,
        )

    result = routed_chat(
        msgs,
        intent=intent or "llm",
        model=mid,
        provider=provider,
        max_tokens=max_tok,
        temperature=temp,
        agent_id=agent,
        consumer=consumer,
        request_class=rclass,
        prefer_free=prefer_free,
    )

    if not result.get("ok"):
        err, code = map_tollgate_error(result)
        return JSONResponse(err, status_code=code)

    return to_openai_completion(result, model=body.model or "tollgate", consumer=consumer)


# ── Anthropic-compatible drop-in ──────────────────────────────────────


class AnthropicMessagesBody(BaseModel):
    model: str = "tollgate/auto"
    messages: list[dict[str, Any]] = Field(default_factory=list)
    max_tokens: int = 1024
    system: str | list[Any] | None = None
    temperature: float | None = 1.0
    stream: bool = False
    metadata: dict[str, Any] | None = None
    # Tollgate extras
    intent: str | None = None
    provider: str | None = None
    request_class: str | None = None
    prefer_free: bool | None = None


@app.post("/v1/messages")
def anthropic_messages(
    body: AnthropicMessagesBody,
    x_consumer_key: str | None = Header(default=None, alias="X-Consumer-Key"),
    x_consumer_id: str | None = Header(default=None, alias="X-Consumer-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
    anthropic_version: str | None = Header(default=None, alias="anthropic-version"),
) -> Any:
    """
    Anthropic-compatible Messages API (admission + route + meter).

    Drop-in::

        export ANTHROPIC_BASE_URL=http://127.0.0.1:8787
        export ANTHROPIC_API_KEY=n8n:secret   # open mode: any label

        # or curl with x-api-key
        curl -s http://127.0.0.1:8787/v1/messages \\
          -H 'x-api-key: desk' -H 'anthropic-version: 2023-06-01' \\
          -H 'content-type: application/json' \\
          -d '{"model":"tollgate/free","max_tokens":64,"messages":[{"role":"user","content":"hi"}]}'

    Does **not** require an Anthropic provider key — routes through Tollgate LLMs.
    ``anthropic-version`` is accepted and ignored (compat).
    """
    _ = anthropic_version  # accepted for SDK compat
    auth = _require(
        x_consumer_key,
        x_consumer_id,
        authorization=authorization,
        x_api_key=x_api_key,
    )
    consumer = auth["consumer"]

    from tollgate.anthropic_compat import (
        anthropic_error,
        map_anthropic_error,
        normalize_anthropic_messages,
        stream_anthropic_from_openai_sse,
        to_anthropic_message,
    )

    msgs = normalize_anthropic_messages(body.messages, system=body.system)
    # strip system-only → need at least one user/assistant turn for most providers
    userish = [m for m in msgs if m.get("role") != "system"]
    if not userish:
        err, code = anthropic_error("messages is required", status=400)
        return JSONResponse(err, status_code=code)

    intent = (body.intent or "").strip()
    prefer_free = body.prefer_free
    if not intent:
        intent, auto_free = resolve_intent(body.model, prefer_free=prefer_free)
        if prefer_free is None:
            prefer_free = auto_free
    else:
        prefer_free = bool(prefer_free) if prefer_free is not None else intent == "free_llm"

    mid = (body.model or "").strip()
    provider = (body.provider or "").strip()
    # claude-* / tollgate/* → let router pick provider/model
    if mid.startswith("tollgate/") or mid.lower().startswith("claude"):
        route_model = ""
    else:
        route_model = mid
    rclass = (body.request_class or "interactive").strip() or "interactive"
    meta_user = ""
    if isinstance(body.metadata, dict):
        meta_user = str(body.metadata.get("user_id") or body.metadata.get("user") or "")[:64]
    agent = (meta_user or f"anthropic:{consumer}")[:64]
    max_tok = max(1, int(body.max_tokens or 1024))
    temp = float(body.temperature if body.temperature is not None else 0.7)

    if body.stream:
        from tollgate.chat_stream import start_chat_stream

        started = start_chat_stream(
            msgs,
            intent=intent or "llm",
            model=route_model,
            provider=provider,
            max_tokens=max_tok,
            temperature=temp,
            agent_id=agent,
            consumer=consumer,
            request_class=rclass,
            prefer_free=prefer_free,
            requested_model=body.model or "tollgate",
        )
        if not started.get("ok"):
            err, code = map_anthropic_error(started)
            return JSONResponse(err, status_code=code)
        headers = {
            "Cache-Control": "no-cache",
            "X-Tollgate-Consumer": consumer,
            "X-Tollgate-Stream": str(started.get("mode") or "upstream"),
            "X-Tollgate-Provider": str(started.get("provider") or ""),
            "X-Tollgate-Compat": "anthropic",
        }
        # chat_stream yields OpenAI SSE → convert to Anthropic event stream
        anthro_stream = stream_anthropic_from_openai_sse(
            started["stream"],
            model=body.model or str(started.get("model") or "tollgate"),
            provider=str(started.get("provider") or ""),
            consumer=consumer,
        )
        return StreamingResponse(
            anthro_stream,
            media_type="text/event-stream",
            headers=headers,
        )

    result = routed_chat(
        msgs,
        intent=intent or "llm",
        model=route_model,
        provider=provider,
        max_tokens=max_tok,
        temperature=temp,
        agent_id=agent,
        consumer=consumer,
        request_class=rclass,
        prefer_free=prefer_free,
    )
    if not result.get("ok"):
        err, code = map_anthropic_error(result)
        return JSONResponse(err, status_code=code)
    return to_anthropic_message(result, model=body.model or "tollgate", consumer=consumer)


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "tollgate",
        "product": "Tollgate",
        "docs": "/docs",
        "repo": "https://github.com/landjunge/tollgate",
        "openai_base_url": "/v1",
        "openai": ["/v1/chat/completions", "/v1/models"],
        "anthropic_base_url": "/",
        "anthropic": ["/v1/messages"],
        "control": "/v1/control",
        "resilience": "/v1/resilience",
        "chaos": "/v1/chaos",
        "dashboard": "/dashboard",
        "vision": "docs/VISION.md",
        "product": "docs/PRODUCT.md",
        "architecture": "docs/ARCHITECTURE.md",
        "mcp": "docs/MCP.md",
        "portable": "docs/PORTABLE.md",
        "cost_limits": "docs/COST_LIMITS.md",
        "metrics": "/metrics",
        "v1": [
            "/v1/health",
            "/v1/auth",
            "/v1/control",
            "/v1/resilience",
            "/v1/chaos",
            "/v1/models",
            "/v1/chat/completions",
            "/v1/messages",
            "/v1/route",
            "/v1/invoke",
            "/v1/budget",
            "/v1/providers",
            "/v1/usage",
            "/v1/config",
        ],
    }
