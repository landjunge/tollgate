"""DeepSeek / Worker keys — OpenAI-compatible, concurrency-limited."""

from __future__ import annotations

from typing import Any

from tollgate.secrets import is_usable_api_key
from tollgate.base import as_status, get_env, mask_secret
from tollgate.httputil import http_json
from tollgate.research_notes import research_for

BASE = "https://api.deepseek.com"


def api_key(*, worker: bool = False) -> str:
    if worker:
        return get_env("WORKER_API_KEY") or get_env("DEEPSEEK_API_KEY")
    return get_env("DEEPSEEK_API_KEY")


def default_model() -> str:
    return get_env("DEEPSEEK_MODEL", default="deepseek-v4-flash")


def list_models(*, worker: bool = False) -> dict[str, Any]:
    key = api_key(worker=worker)
    if not is_usable_api_key(key):
        return {"ok": False, "error": "API key missing", "models": []}
    r = http_json(
        "GET",
        f"{BASE}/models",
        headers={"Authorization": f"Bearer {key}"},
    )
    if not r["ok"]:
        return {"ok": False, "error": r["error"], "models": [], "status": r["status"]}
    data = r["data"] if isinstance(r["data"], dict) else {}
    models = [m.get("id") for m in (data.get("data") or []) if isinstance(m, dict)]
    return {
        "ok": True,
        "models": models,
        "default_model": default_model(),
        "research": {
            "concurrency_flash": research_for("deepseek").get("limits", {}).get("flash_concurrent"),
            "concurrency_pro": research_for("deepseek").get("limits", {}).get("pro_concurrent"),
        },
    }


def status(*, live: bool = False, worker: bool = False) -> dict[str, Any]:
    pid = "worker" if worker else "deepseek"
    key = api_key(worker=worker)
    env_name = "WORKER_API_KEY" if worker else "DEEPSEEK_API_KEY"
    masked = {env_name: mask_secret(get_env(env_name))}
    if not worker:
        masked["DEEPSEEK_MODEL"] = default_model()
    else:
        masked["falls_back"] = "yes" if not get_env("WORKER_API_KEY") else "no"

    if not is_usable_api_key(key):
        return as_status(
            id=pid,
            ready=False,
            error=f"{env_name} missing",
            masked=masked,
            detail={"research": research_for(pid)},
        )
    if not live:
        return as_status(
            id=pid,
            ready=True,
            masked=masked,
            detail={
                "live": False,
                "model": default_model(),
                "research_limits": research_for("deepseek").get("limits"),
            },
        )
    models = list_models(worker=worker)
    return as_status(
        id=pid,
        ready=bool(models.get("ok")),
        error=models.get("error"),
        masked=masked,
        detail={
            "live": True,
            "models": (models.get("models") or [])[:12],
            "default_model": default_model(),
            "research_limits": research_for("deepseek").get("limits"),
        },
    )
