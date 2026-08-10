"""Brave Search — X-Subscription-Token + rate-limit headers."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlencode

from tollgate.secrets import is_usable_api_key
from tollgate.base import as_status, get_env, mask_secret
from tollgate.httputil import http_json
from tollgate.research_notes import research_for

BASE = "https://api.search.brave.com"
# Live inventory must not burn quota every call
_QUOTA_TTL_S = 60.0
_quota_cache: dict[str, Any] = {"ts": 0.0, "data": None}


def api_key() -> str:
    return get_env("BRAVE_API_KEY")


def _headers() -> dict[str, str]:
    return {
        "X-Subscription-Token": api_key(),
        "Accept": "application/json",
        "User-Agent": "gnom-hub/keys brave",
    }


def quota(*, q: str = "ping", force: bool = False) -> dict[str, Any]:
    """
    One cheap search to read X-RateLimit-* (Brave has no dedicated quota endpoint).

    Costs 1 successful request against monthly quota.
    Results cached for 60s (plan D3).
    """
    if not is_usable_api_key(api_key()):
        return {"ok": False, "error": "BRAVE_API_KEY missing", "rate": {}}
    now = time.time()
    if (
        not force
        and _quota_cache["data"] is not None
        and (now - float(_quota_cache["ts"])) < _QUOTA_TTL_S
    ):
        cached = dict(_quota_cache["data"])  # type: ignore[arg-type]
        cached["cached"] = True
        return cached

    params = urlencode({"q": (q or "ping")[:80], "count": "1"})
    r = http_json(
        "GET",
        f"{BASE}/res/v1/web/search?{params}",
        headers=_headers(),
    )
    rate = r.get("rate") or {}
    out = {
        "ok": bool(r.get("ok")),
        "status": r.get("status"),
        "error": r.get("error"),
        "rate": rate,
        "per_second_remaining": rate.get("per_second_remaining"),
        "period_remaining": rate.get("period_remaining"),
        "per_second_limit": rate.get("per_second_limit"),
        "period_limit": rate.get("period_limit"),
        "research": research_for("brave").get("limits"),
        "cached": False,
    }
    if out["ok"]:
        _quota_cache["ts"] = now
        _quota_cache["data"] = dict(out)
    return out


def search(
    query: str,
    *,
    count: int = 5,
    country: str = "DE",
    search_lang: str = "de",
) -> dict[str, Any]:
    """Web search; returns results + rate headers for callers to throttle."""
    if not is_usable_api_key(api_key()):
        return {"ok": False, "error": "BRAVE_API_KEY missing", "results": []}
    q = " ".join(str(query or "").split()).strip()
    if not q:
        return {"ok": False, "error": "empty query", "results": []}
    # API: max 400 chars / 50 words; count 1–20
    words = q.split()
    if len(words) > 50:
        q = " ".join(words[:50])
    q = q[:400]
    n = max(1, min(20, int(count or 5)))
    params = urlencode(
        {
            "q": q,
            "count": str(n),
            "country": (country or "DE")[:2].upper(),
            "search_lang": (search_lang or "de")[:2].lower(),
        }
    )
    r = http_json(
        "GET",
        f"{BASE}/res/v1/web/search?{params}",
        headers=_headers(),
    )
    if not r.get("ok"):
        return {
            "ok": False,
            "error": r.get("error") or f"HTTP {r.get('status')}",
            "query": q,
            "results": [],
            "rate": r.get("rate") or {},
        }
    data = r.get("data") if isinstance(r.get("data"), dict) else {}
    web = (data.get("web") or {}) if isinstance(data, dict) else {}
    raw = web.get("results") or []
    results: list[dict[str, str]] = []
    for item in raw[:n]:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "title": str(item.get("title") or "")[:200],
                "url": str(item.get("url") or "")[:500],
                "description": str(item.get("description") or "")[:400],
            }
        )
    rate = r.get("rate") or {}
    return {
        "ok": True,
        "query": q,
        "count": len(results),
        "results": results,
        "rate": rate,
        "period_remaining": rate.get("period_remaining"),
        "per_second_remaining": rate.get("per_second_remaining"),
    }


def status(*, live: bool = False) -> dict[str, Any]:
    key = api_key()
    masked = {"BRAVE_API_KEY": mask_secret(key)}
    if not is_usable_api_key(key):
        return as_status(
            id="brave",
            ready=False,
            error="BRAVE_API_KEY missing",
            masked=masked,
            detail={"research": research_for("brave")},
        )
    if not live:
        return as_status(
            id="brave",
            ready=True,
            masked=masked,
            detail={
                "live": False,
                "auth": "X-Subscription-Token",
                "limits": research_for("brave").get("limits"),
                "gotchas": research_for("brave").get("gotchas"),
            },
        )
    q = quota()
    return as_status(
        id="brave",
        ready=bool(q.get("ok")),
        error=q.get("error"),
        masked=masked,
        detail={
            "live": True,
            "period_remaining": q.get("period_remaining"),
            "period_limit": q.get("period_limit"),
            "per_second_limit": q.get("per_second_limit"),
            "per_second_remaining": q.get("per_second_remaining"),
            "rate": q.get("rate"),
            "gotchas": research_for("brave").get("gotchas"),
        },
    )
