"""Thin re-exports — prefer dedicated modules (deepseek, openrouter, …)."""

from __future__ import annotations

from typing import Any

from tollgate import deepseek as deepseek_mod
from tollgate import minimax as minimax_mod
from tollgate import nvidia as nvidia_mod
from tollgate import openrouter as openrouter_mod
from tollgate.base import as_status, get_env, mask_secret
from tollgate.secrets import is_usable_api_key
from tollgate.httputil import http_json
from tollgate.research_notes import research_for


def deepseek_status(*, live: bool = False) -> dict[str, Any]:
    return deepseek_mod.status(live=live, worker=False)


def worker_status(*, live: bool = False) -> dict[str, Any]:
    return deepseek_mod.status(live=live, worker=True)


def openrouter_status(*, live: bool = False) -> dict[str, Any]:
    return openrouter_mod.status(live=live)


def nvidia_status(*, live: bool = False) -> dict[str, Any]:
    return nvidia_mod.status(live=live)


def minimax_status(*, live: bool = False) -> dict[str, Any]:
    return minimax_mod.status(live=live)


def opencode_zen_status(*, live: bool = False) -> dict[str, Any]:
    from tollgate import opencode_zen as zen_mod

    return zen_mod.status(live=live)


def telegram_status(*, live: bool = False) -> dict[str, Any]:
    token = get_env("TELEGRAM_BOT_TOKEN")
    masked = {"TELEGRAM_BOT_TOKEN": mask_secret(token)}
    if not is_usable_api_key(token):
        return as_status(
            id="telegram",
            ready=False,
            error="TELEGRAM_BOT_TOKEN not set",
            masked=masked,
            detail={"optional": True, "research": research_for("telegram")},
        )
    if not live:
        return as_status(
            id="telegram",
            ready=True,
            masked=masked,
            detail={"live": False, "optional": True},
        )
    r = http_json("GET", f"https://api.telegram.org/bot{token}/getMe")
    ok = bool(r.get("ok") and isinstance(r.get("data"), dict) and r["data"].get("ok"))
    username = None
    if ok:
        username = (r["data"].get("result") or {}).get("username")
    return as_status(
        id="telegram",
        ready=ok,
        error=None if ok else (r.get("error") or "getMe failed"),
        masked=masked,
        detail={"live": True, "username": username, "optional": True},
    )
