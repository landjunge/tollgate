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


def chat(
    messages: list[dict[str, str]] | str = "hi",
    *,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    worker: bool = False,
    **_kw: Any,
) -> dict[str, Any]:
    """OpenAI-compatible chat/completions (system + worker keys)."""
    key = api_key(worker=worker)
    if not is_usable_api_key(key):
        env_name = "WORKER_API_KEY" if worker else "DEEPSEEK_API_KEY"
        return {"ok": False, "error": f"{env_name} missing"}
    if isinstance(messages, str):
        msgs: list[dict[str, str]] = [{"role": "user", "content": messages[:8000]}]
    else:
        msgs = [
            {"role": str(m.get("role") or "user"), "content": str(m.get("content") or "")[:16000]}
            for m in (messages or [])
            if isinstance(m, dict)
        ]
        if not msgs:
            msgs = [{"role": "user", "content": "hi"}]
    mid = (model or default_model() or "deepseek-v4-flash").strip()
    r = http_json(
        "POST",
        f"{BASE}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        body={
            "model": mid,
            "messages": msgs,
            "stream": False,
            "temperature": float(temperature),
            "max_tokens": max(1, min(128_000, int(max_tokens or 1024))),
        },
        timeout=120.0,
    )
    if not r.get("ok"):
        return {
            "ok": False,
            "error": r.get("error") or f"HTTP {r.get('status')}",
            "status": r.get("status"),
            "model": mid,
            "provider": "worker" if worker else "deepseek",
        }
    data = r.get("data") if isinstance(r.get("data"), dict) else {}
    choices = data.get("choices") or []
    content = ""
    if choices and isinstance(choices[0], dict):
        msg = choices[0].get("message") or {}
        content = str(msg.get("content") or msg.get("reasoning_content") or "")
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    return {
        "ok": True,
        "provider": "worker" if worker else "deepseek",
        "model": data.get("model") or mid,
        "content": content,
        "usage": usage,
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
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
