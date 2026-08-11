"""
Standalone multi-consumer HTTP surface (extractable to own repo).

Run (no full hub UI required):
  PYTHONPATH=src GNOM_WS=... uvicorn tollgate.server_v1:app --host 127.0.0.1 --port 8787

Contract (stable for n8n / agents / future repo):
  GET  /v1/health
  GET  /v1/providers
  GET  /v1/budget
  POST /v1/route
  POST /v1/invoke
  GET  /v1/usage
  GET  /v1/config   (local desk; lock down later with consumer auth)
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from tollgate import get_keys_service
from tollgate.gateway.context import RequestClass, RequestContext
from tollgate.gateway.entry import gateway_call


def _bootstrap_env() -> None:
    try:
        from tollgate.paths import data_home, user_dir
        from tollgate.secrets import ensure_env_from_key_txt, load_keys, parse_key_file

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
    version="0.1.0",
    description=(
        "Tollgate — multi-consumer API admission + router. "
        "Budgets, circuits, distill-backed providers. "
        "Gnom, n8n, and other agents share this control plane. "
        "https://github.com/landjunge/tollgate"
    ),
)


def _consumer_from_header(x_consumer_key: str | None) -> str:
    """
    Lightweight consumer id until full API-key store lands.

    Header: X-Consumer-Key: n8n | gnom | cursor | ...
    (Phase 3: map to hashed secrets + per-consumer budgets.)
    """
    c = (x_consumer_key or "anonymous").strip() or "anonymous"
    return c[:64]


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
    request_class: str = "interactive"  # interactive|batch|free|system
    allow_paid_fallback: bool = False


@app.get("/v1/health")
def health() -> dict[str, Any]:
    from tollgate.gateway.circuit import get_circuits

    ks = get_keys_service()
    return {
        "ok": True,
        "service": "tollgate",
        "product": "Tollgate",
        "version": "0.1.0",
        "extractable": True,
        "multi_consumer": True,
        "app": ks.app_status(),
        "circuits": get_circuits().snapshot()[:30],
    }


@app.get("/v1/providers")
def providers(live: bool = Query(False)) -> dict[str, Any]:
    return get_keys_service().inventory(live=live)


@app.get("/v1/budget")
def budget(
    provider: str = Query(""),
    tokens_est: int = Query(0, ge=0),
    chars_est: int = Query(0, ge=0),
) -> dict[str, Any]:
    ks = get_keys_service()
    if provider.strip():
        return {
            "ok": True,
            "provider": provider,
            "limits": ks.check_provider_limits(
                provider, tokens_est=tokens_est, chars_est=chars_est
            ),
            "usage": ks.usage(),
        }
    return {"ok": True, "usage": ks.usage(), "config": ks.get_config().get("config", {}).get("cost_guard")}


@app.post("/v1/route")
def route(
    body: RouteBody,
    x_consumer_key: str | None = Header(default=None, alias="X-Consumer-Key"),
) -> dict[str, Any]:
    consumer = _consumer_from_header(x_consumer_key)
    out = get_keys_service().route(
        body.intent,
        tokens_est=body.tokens_est,
        chars_est=body.chars_est,
        live=body.live,
    )
    out["consumer"] = consumer
    return out


@app.post("/v1/invoke")
def invoke(
    body: InvokeBody,
    x_consumer_key: str | None = Header(default=None, alias="X-Consumer-Key"),
) -> dict[str, Any]:
    """
    Multi-consumer admit + call + meter.

    n8n / agents should use this instead of holding provider secrets.
    """
    consumer = _consumer_from_header(x_consumer_key)
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
def usage() -> dict[str, Any]:
    return get_keys_service().usage()


@app.get("/v1/config")
def config_get() -> dict[str, Any]:
    # Phase 3: require consumer admin scope
    return get_keys_service().get_config()


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "tollgate",
        "product": "Tollgate",
        "docs": "/docs",
        "vision": "docs/keys/VISION.md",
        "v1": ["/v1/health", "/v1/route", "/v1/invoke", "/v1/budget", "/v1/providers"],
    }
