"""Google/Gemini — high-risk; presence only unless explicitly enabled."""

from __future__ import annotations

from typing import Any

from tollgate.secrets import is_usable_api_key
from tollgate.app_config import is_provider_enabled, provider_cfg
from tollgate.base import as_status, get_env, mask_secret
from tollgate.distill.loader import research_view


def api_key() -> str:
    return get_env("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_AI_API_KEY")


def status(*, live: bool = False) -> dict[str, Any]:
    key = api_key()
    pcfg = provider_cfg("google")
    enabled = is_provider_enabled("google")
    masked = {
        "GOOGLE_API_KEY": mask_secret(get_env("GOOGLE_API_KEY")),
        "GEMINI_API_KEY": mask_secret(get_env("GEMINI_API_KEY")),
        "enabled": "true" if enabled else "false",
        "max_usd_day": str(pcfg.get("max_usd_day") or ""),
        "max_calls_day": str(pcfg.get("max_calls_day") or ""),
    }
    research = research_view("google")
    if not enabled:
        return as_status(
            id="google",
            ready=False,
            error=(
                "DISABLED (high cost risk). Google/Gemini bills fast and is complex. "
                "Enable only in keys_app.json with max_usd_day + max_calls_day caps."
            ),
            masked=masked,
            detail={
                "live": False,
                "high_risk": True,
                "cost_warning": research.get("cost_warning")
                or research.get("gotchas"),
                "research": research,
            },
        )
    if not is_usable_api_key(key):
        return as_status(
            id="google",
            ready=False,
            error="GOOGLE_API_KEY / GEMINI_API_KEY missing",
            masked=masked,
            detail={"high_risk": True, "research": research},
        )
    # No automatic live spend probe — too easy to burn money
    return as_status(
        id="google",
        ready=True,
        masked=masked,
        detail={
            "live": False,
            "high_risk": True,
            "note": "Enabled with hard caps — prefer free Zen/DeepSeek for daily work",
            "limits": {
                "max_usd_day": pcfg.get("max_usd_day"),
                "max_calls_day": pcfg.get("max_calls_day"),
                "max_tokens_day": pcfg.get("max_tokens_day"),
            },
            "research": research,
        },
    )
