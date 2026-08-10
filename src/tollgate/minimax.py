"""MiniMax — region-sensitive; pay-as-you-go key vs Token Plan key."""

from __future__ import annotations

from typing import Any

from tollgate.secrets import is_usable_api_key
from tollgate.base import as_status, get_env, mask_secret
from tollgate.httputil import http_json
from tollgate.research_notes import research_for

BASES = (
    "https://api.minimax.io/v1",
    "https://api.minimaxi.com/v1",
)


def api_key() -> str:
    return get_env("MINIMAX_API_KEY")


def probe_key() -> dict[str, Any]:
    """
    Validate key against international + CN hosts.

    MiniMax returns base_resp.status_code 2049 for invalid keys (sometimes HTTP 200).
    """
    key = api_key()
    if not is_usable_api_key(key):
        return {"ok": False, "error": "MINIMAX_API_KEY missing"}
    tried = []
    for base in BASES:
        r = http_json(
            "GET",
            f"{base}/files/list",
            headers={"Authorization": f"Bearer {key}"},
        )
        data = r.get("data") if isinstance(r.get("data"), dict) else {}
        base_resp = data.get("base_resp") if isinstance(data, dict) else None
        code_mm = None
        if isinstance(base_resp, dict):
            code_mm = base_resp.get("status_code")
        tried.append(
            {
                "base": base,
                "http": r.get("status"),
                "ok": r.get("ok"),
                "minimax_code": code_mm,
                "error": r.get("error"),
            }
        )
        # success: HTTP ok and no 2049
        if r.get("ok") and code_mm not in (2049, "2049"):
            if code_mm in (0, None, "0"):
                return {"ok": True, "base": base, "tried": tried}
            # some success payloads omit base_resp
            if code_mm is None and r.get("status") == 200:
                return {"ok": True, "base": base, "tried": tried}
    return {
        "ok": False,
        "error": "MiniMax key invalid or wrong region (2049 / 401)",
        "tried": tried,
        "research": research_for("minimax").get("gotchas"),
    }


def status(*, live: bool = False) -> dict[str, Any]:
    key = api_key()
    masked = {
        "MINIMAX_API_KEY": mask_secret(key),
        "MINIMAX_GROUP_ID": get_env("MINIMAX_GROUP_ID") or "(unset)",
    }
    if not is_usable_api_key(key):
        return as_status(
            id="minimax",
            ready=False,
            error="MINIMAX_API_KEY missing",
            masked=masked,
            detail={"research": research_for("minimax")},
        )
    if not live:
        # Presence alone is NOT ready (2049 invalid keys are common)
        return as_status(
            id="minimax",
            ready=False,
            error="unverified — run live probe (presence ≠ ready)",
            masked=masked,
            detail={
                "live": False,
                "key_present": True,
                "note": "MINIMAX must pass live probe; 2049 = invalid",
                "gotchas": research_for("minimax").get("gotchas"),
            },
        )
    p = probe_key()
    return as_status(
        id="minimax",
        ready=bool(p.get("ok")),
        error=p.get("error"),
        masked=masked,
        detail={"live": True, **{k: v for k, v in p.items() if k != "ok"}},
    )
