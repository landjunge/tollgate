"""ElevenLabs key specials: subscription + credit reserve floor."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from tollgate.secrets import is_usable_api_key
from tollgate.base import as_status, get_env, mask_secret

_DEFAULT_MIN_REMAINING = 5000
_CACHE_TTL_S = 30.0
_cache: dict[str, Any] = {"ts": 0.0, "data": None}


def api_key() -> str:
    return get_env("ELEVENLABS_API_KEY")


def min_remaining() -> int:
    raw = get_env("ELEVENLABS_MIN_REMAINING", default=str(_DEFAULT_MIN_REMAINING))
    try:
        return max(0, int(raw))
    except ValueError:
        return _DEFAULT_MIN_REMAINING


def voice_id() -> str:
    return get_env("ELEVENLABS_VOICE_ID")


def fetch_subscription(*, force: bool = False) -> dict[str, Any]:
    """Live subscription: used / limit / remaining / allowed_spend."""
    now = time.time()
    if not force and _cache["data"] is not None and (now - float(_cache["ts"])) < _CACHE_TTL_S:
        return dict(_cache["data"])  # type: ignore[arg-type]

    key = api_key()
    if not is_usable_api_key(key):
        return {"ok": False, "error": "ELEVENLABS_API_KEY missing", "remaining": 0}

    req = urllib.request.Request(
        "https://api.elevenlabs.io/v1/user/subscription",
        headers={"xi-api-key": key, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:  # noqa: BLE001
            body = str(e)
        return {"ok": False, "error": f"HTTP {e.code}: {body}", "remaining": 0}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e), "remaining": 0}

    used = int(data.get("character_count") or 0)
    limit = int(data.get("character_limit") or 0)
    remaining = max(0, limit - used)
    floor = min_remaining()
    out = {
        "ok": True,
        "character_count": used,
        "character_limit": limit,
        "remaining": remaining,
        "tier": data.get("tier"),
        "min_remaining": floor,
        "allowed_spend": max(0, remaining - floor),
        "voice_id": voice_id() or None,
        "key_name": os.environ.get("ELEVENLABS_KEY_NAME") or None,
    }
    _cache["ts"] = now
    _cache["data"] = out
    return dict(out)


def check_budget(*, cost: int = 0) -> dict[str, Any]:
    """
    Allow usage until remaining would drop to ELEVENLABS_MIN_REMAINING.

    cost ≈ credits for next call (TTS chars ≈ 1:1 on multilingual v2).
    """
    floor = min_remaining()
    sub = fetch_subscription()
    if not sub.get("ok"):
        return {
            "ok": False,
            "allowed": False,
            "error": sub.get("error") or "subscription check failed",
            "min_remaining": floor,
        }

    remaining = int(sub.get("remaining") or 0)
    need = max(0, int(cost or 0))
    after = remaining - need
    allowed = after >= floor if need else remaining > floor
    if remaining <= floor:
        allowed = False

    return {
        "ok": True,
        "allowed": allowed,
        "remaining": remaining,
        "after": after if need else remaining,
        "cost": need,
        "min_remaining": floor,
        "allowed_spend": max(0, remaining - floor),
        "character_count": sub.get("character_count"),
        "character_limit": sub.get("character_limit"),
        "tier": sub.get("tier"),
        "error": None
        if allowed
        else (
            f"ElevenLabs reserve reached: remaining={remaining}, "
            f"floor={floor} (ELEVENLABS_MIN_REMAINING). "
            f"Allowed spend left: {max(0, remaining - floor)}."
        ),
    }


def ensure_budget(*, cost: int = 0) -> dict[str, Any]:
    r = check_budget(cost=cost)
    if not r.get("allowed"):
        raise ValueError(r.get("error") or "ElevenLabs budget blocked")
    return r


def status(*, live: bool = True) -> dict[str, Any]:
    key = api_key()
    masked = {
        "ELEVENLABS_API_KEY": mask_secret(key),
        "ELEVENLABS_MIN_REMAINING": str(min_remaining()),
        "ELEVENLABS_VOICE_ID": voice_id() or "",
    }
    if not is_usable_api_key(key):
        return as_status(
            id="elevenlabs",
            ready=False,
            error="ELEVENLABS_API_KEY missing",
            masked=masked,
        )
    if not live:
        return as_status(
            id="elevenlabs",
            ready=True,
            masked=masked,
            detail={"min_remaining": min_remaining(), "live": False},
        )
    budget = check_budget(cost=0)
    # ready = key authenticates; spend may still be blocked by reserve floor
    live_ok = bool(budget.get("ok"))
    return as_status(
        id="elevenlabs",
        ready=live_ok,
        error=None if live_ok else budget.get("error"),
        masked=masked,
        detail={
            "remaining": budget.get("remaining"),
            "allowed_spend": budget.get("allowed_spend"),
            "min_remaining": budget.get("min_remaining"),
            "tier": budget.get("tier"),
            "allowed": budget.get("allowed"),
            "live": True,
        },
    )
