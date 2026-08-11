"""
Standalone multi-consumer HTTP surface.

  tollgate serve
  → http://127.0.0.1:8787/docs

Contract:
  GET  /v1/health
  GET  /v1/providers
  GET  /v1/budget
  POST /v1/route
  POST /v1/invoke
  GET  /v1/usage
  GET|POST /v1/config   (admin when auth mode)
  GET  /v1/auth
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from tollgate import get_keys_service
from tollgate.consumers import auth_status, verify_consumer
from tollgate.gateway.context import RequestClass, RequestContext
from tollgate.gateway.entry import gateway_call


def _bootstrap_env() -> None:
    try:
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
    except Exception:  # noqa: BLE001
        pass


_bootstrap_env()

app = FastAPI(
    title="Tollgate",
    version="0.1.2",
    description=(
        "Tollgate — multi-consumer API admission + router. "
        "Budgets, circuits, distill-backed providers. "
        "Portable/USB friendly. "
        "https://github.com/landjunge/tollgate"
    ),
)


def _require(
    x_consumer_key: str | None,
    x_consumer_id: str | None = None,
    *,
    need_admin: bool = False,
) -> dict[str, Any]:
    auth = verify_consumer(x_consumer_key, x_consumer_id, need_admin=need_admin)
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
        "version": "0.1.2",
        "extractable": True,
        "multi_consumer": True,
        "portable": path_snapshot(),
        "auth": auth_status(),
        "app": ks.app_status(),
        "circuits": get_circuits().snapshot()[:30],
    }


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
) -> dict[str, Any]:
    """Read keys_app.json policy (admin when auth mode)."""
    auth = _require(x_consumer_key, x_consumer_id, need_admin=True)
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
) -> dict[str, Any]:
    """Deep-merge patch into keys_app.json (admin when auth mode)."""
    auth = _require(x_consumer_key, x_consumer_id, need_admin=True)
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


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "tollgate",
        "product": "Tollgate",
        "docs": "/docs",
        "repo": "https://github.com/landjunge/tollgate",
        "vision": "docs/VISION.md",
        "architecture": "docs/ARCHITECTURE.md",
        "mcp": "docs/MCP.md",
        "portable": "docs/PORTABLE.md",
        "cost_limits": "docs/COST_LIMITS.md",
        "v1": [
            "/v1/health",
            "/v1/auth",
            "/v1/route",
            "/v1/invoke",
            "/v1/budget",
            "/v1/providers",
            "/v1/usage",
            "/v1/config",
        ],
    }
