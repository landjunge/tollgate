"""OpenCode Zen gateway — free + paid models via https://opencode.ai/zen/v1."""

from __future__ import annotations

from typing import Any

from tollgate.secrets import is_usable_api_key
from tollgate.base import as_status, get_env, mask_secret
from tollgate.httputil import http_json
from tollgate.research_notes import research_for

BASE = "https://opencode.ai/zen/v1"
# Cloudflare error 1010 blocks bare Python UA — use a normal browser UA
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 "
    "gnom-hub/keys-opencode-zen"
)

# Free models from official Zen docs (ids without opencode/ prefix for API)
FREE_MODELS = (
    "deepseek-v4-flash-free",
    "mimo-v2.5-free",
    "laguna-s-2.1-free",
    "ling-3.0-tiny-free",
    "longcat-2.0-free",
    "north-mini-code-free",
    "nemotron-3-ultra-free",
    "big-pickle",
)


def api_key() -> str:
    # Official env is OPENCODE_API_KEY; we also accept OPENCODE_ZEN_API_KEY
    return get_env("OPENCODE_API_KEY", "OPENCODE_ZEN_API_KEY")


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key()}",
        "Accept": "application/json",
        "User-Agent": _UA,
    }


def list_models() -> dict[str, Any]:
    key = api_key()
    if not is_usable_api_key(key):
        return {"ok": False, "error": "OPENCODE_API_KEY / OPENCODE_ZEN_API_KEY missing", "models": []}
    r = http_json("GET", f"{BASE}/models", headers=_headers())
    if not r.get("ok"):
        return {
            "ok": False,
            "error": r.get("error") or f"HTTP {r.get('status')}",
            "status": r.get("status"),
            "models": [],
            "hint": (
                "Cloudflare 1010 = bot block — retry with browser UA "
                "(this client sets one). Auth issues are 401/402."
            )
            if r.get("status") == 403
            else None,
        }
    data = r.get("data") if isinstance(r.get("data"), dict) else {}
    models = [m.get("id") for m in (data.get("data") or []) if isinstance(m, dict)]
    free = [m for m in models if isinstance(m, str) and ("free" in m or m == "big-pickle")]
    return {
        "ok": True,
        "count": len(models),
        "free_count": len(free),
        "free_models": free[:20] or list(FREE_MODELS),
        "sample": models[:15],
        "base_url": BASE,
    }


def chat(
    message: str,
    *,
    model: str = "deepseek-v4-flash-free",
    max_tokens: int = 64,
) -> dict[str, Any]:
    """Minimal chat completions probe (free models cost $0)."""
    key = api_key()
    if not is_usable_api_key(key):
        return {"ok": False, "error": "OPENCODE_API_KEY missing"}
    mid = (model or "deepseek-v4-flash-free").removeprefix("opencode/")
    r = http_json(
        "POST",
        f"{BASE}/chat/completions",
        headers=_headers(),
        body={
            "model": mid,
            "messages": [{"role": "user", "content": str(message or "hi")[:500]}],
            "max_tokens": max(1, min(512, int(max_tokens or 64))),
        },
    )
    if not r.get("ok"):
        return {
            "ok": False,
            "error": r.get("error") or f"HTTP {r.get('status')}",
            "status": r.get("status"),
            "model": mid,
        }
    data = r.get("data") if isinstance(r.get("data"), dict) else {}
    choices = data.get("choices") or []
    content = ""
    if choices and isinstance(choices[0], dict):
        msg = choices[0].get("message") or {}
        content = str(msg.get("content") or msg.get("reasoning_content") or "")[:500]
    return {
        "ok": True,
        "model": data.get("model") or mid,
        "content": content,
        "usage": data.get("usage"),
        "cost": data.get("cost"),
    }


def status(*, live: bool = False) -> dict[str, Any]:
    key = api_key()
    env_used = "OPENCODE_API_KEY" if get_env("OPENCODE_API_KEY") else "OPENCODE_ZEN_API_KEY"
    masked = {
        "OPENCODE_API_KEY": mask_secret(get_env("OPENCODE_API_KEY")),
        "OPENCODE_ZEN_API_KEY": mask_secret(get_env("OPENCODE_ZEN_API_KEY")),
        "active_env": env_used if key else "(none)",
    }
    if not is_usable_api_key(key):
        return as_status(
            id="opencode_zen",
            ready=False,
            error="OPENCODE_API_KEY / OPENCODE_ZEN_API_KEY missing",
            masked=masked,
            detail={"research": research_for("opencode_zen"), "base_url": BASE},
        )
    if not live:
        return as_status(
            id="opencode_zen",
            ready=True,
            masked=masked,
            detail={
                "live": False,
                "base_url": BASE,
                "free_models": list(FREE_MODELS),
                "note": (
                    "live=1 runs GET /models (+ optional free chat). "
                    "Needs browser-like User-Agent (Cloudflare). "
                    "$ balance pays paid models; free *-free models cost $0."
                ),
            },
        )
    models = list_models()
    if not models.get("ok"):
        return as_status(
            id="opencode_zen",
            ready=False,
            error=models.get("error"),
            masked=masked,
            detail={"live": True, **models},
        )
    # Prove free chat works (cheap)
    chat_r = chat("ping", model="deepseek-v4-flash-free", max_tokens=8)
    return as_status(
        id="opencode_zen",
        ready=bool(chat_r.get("ok")),
        error=None if chat_r.get("ok") else chat_r.get("error"),
        masked=masked,
        detail={
            "live": True,
            "model_count": models.get("count"),
            "free_count": models.get("free_count"),
            "free_models": models.get("free_models"),
            "chat_probe": {
                "ok": chat_r.get("ok"),
                "model": chat_r.get("model"),
                "cost": chat_r.get("cost"),
            },
            "base_url": BASE,
        },
    )
