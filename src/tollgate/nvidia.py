"""NVIDIA NIM cloud — integrate.api.nvidia.com OpenAI-compatible catalog."""

from __future__ import annotations

from typing import Any

from tollgate.secrets import is_usable_api_key
from tollgate.base import as_status, get_env, mask_secret
from tollgate.httputil import http_json
from tollgate.research_notes import research_for

BASE = "https://integrate.api.nvidia.com/v1"


def api_key() -> str:
    return get_env("NVIDIA_API_KEY")


def list_models() -> dict[str, Any]:
    key = api_key()
    if not is_usable_api_key(key):
        return {"ok": False, "error": "NVIDIA_API_KEY missing", "models": []}
    r = http_json(
        "GET",
        f"{BASE}/models",
        headers={"Authorization": f"Bearer {key}"},
    )
    if not r["ok"]:
        return {"ok": False, "error": r["error"], "status": r["status"], "models": []}
    data = r["data"] if isinstance(r["data"], dict) else {}
    models = [m.get("id") for m in (data.get("data") or []) if isinstance(m, dict)]
    return {"ok": True, "count": len(models), "models": models[:50], "sample": models[:10]}


def status(*, live: bool = False) -> dict[str, Any]:
    key = api_key()
    masked = {"NVIDIA_API_KEY": mask_secret(key)}
    if not is_usable_api_key(key):
        return as_status(
            id="nvidia",
            ready=False,
            error="NVIDIA_API_KEY missing",
            masked=masked,
            detail={"research": research_for("nvidia")},
        )
    if not live:
        return as_status(
            id="nvidia",
            ready=True,
            masked=masked,
            detail={"live": False, "base_url": BASE},
        )
    m = list_models()
    return as_status(
        id="nvidia",
        ready=bool(m.get("ok")),
        error=m.get("error"),
        masked=masked,
        detail={
            "live": True,
            "model_count": m.get("count"),
            "sample": m.get("sample"),
            "gotchas": research_for("nvidia").get("gotchas"),
        },
    )
