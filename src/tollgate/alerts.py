"""
Proactive ops alerts (webhook) — soft warn, hard deny, circuit, chaos.

POST JSON envelope (schema_version 1) to:
  cost_guard.alert_webhook_url  or  TOLLGATE_ALERT_WEBHOOK

CLI:  tollgate alert test
      tollgate alert events
HTTP: POST /v1/alert/test  (admin when auth on)
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from tollgate.app_config import load_config

# de-dupe: don't spam the same key more than once per interval
_LAST: dict[str, float] = {}
_MIN_INTERVAL_S = 300.0
SCHEMA_VERSION = 1

# Catalog — product-facing event types
EVENT_CATALOG: dict[str, dict[str, str]] = {
    "soft_budget": {
        "severity": "warn",
        "description": "Day budget soft pressure (still admitted)",
    },
    "hard_deny": {
        "severity": "error",
        "description": "Admission hard deny (budget/limits/policy)",
    },
    "agent_protection": {
        "severity": "error",
        "description": "Agent loop/rate/$ hard stop",
    },
    "high_risk_block": {
        "severity": "error",
        "description": "High-risk provider blocked (not enabled / no $ cap)",
    },
    "circuit_open": {
        "severity": "warn",
        "description": "Circuit breaker open for provider",
    },
    "chaos_started": {
        "severity": "info",
        "description": "Chaos inject started (DR test)",
    },
    "chaos_stopped": {
        "severity": "info",
        "description": "Chaos inject stopped",
    },
    "chaos_dr_survived": {
        "severity": "info",
        "description": "Failover chaos test survived",
    },
    "chaos_dr_failed": {
        "severity": "error",
        "description": "Failover chaos test failed",
    },
    "webhook_test": {
        "severity": "info",
        "description": "Manual webhook probe (tollgate alert test)",
    },
}


def event_catalog() -> dict[str, Any]:
    return {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "events": [
            {"event": k, **v} for k, v in sorted(EVENT_CATALOG.items())
        ],
        "config": {
            "env": "TOLLGATE_ALERT_WEBHOOK",
            "keys_app": "cost_guard.alert_webhook_url",
            "rate_limit_s": _MIN_INTERVAL_S,
        },
    }


def _webhook_url() -> str:
    env = (os.environ.get("TOLLGATE_ALERT_WEBHOOK") or "").strip()
    if env:
        return env
    guard = load_config().get("cost_guard") or {}
    return str(guard.get("alert_webhook_url") or "").strip()


def _version() -> str:
    try:
        from tollgate import __version__

        return str(__version__)
    except Exception:  # noqa: BLE001
        return "0.3.4"


def _clean_extra(extra: dict[str, Any] | None) -> dict[str, Any]:
    if not extra:
        return {}
    clean: dict[str, Any] = {}
    for k, v in list(extra.items())[:20]:
        kl = str(k)[:40]
        if isinstance(v, (bool, int, float)) or v is None:
            clean[kl] = v
        elif isinstance(v, str):
            clean[kl] = v[:200]
        elif isinstance(v, dict):
            # shallow scalars only
            nested: dict[str, Any] = {}
            for nk, nv in list(v.items())[:12]:
                if isinstance(nv, (bool, int, float)) or nv is None:
                    nested[str(nk)[:32]] = nv
                elif isinstance(nv, str):
                    nested[str(nk)[:32]] = nv[:80]
            if nested:
                clean[kl] = nested
    return clean


def build_alert_payload(
    event: str,
    *,
    provider: str = "",
    message: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Canonical webhook JSON (schema_version 1)."""
    meta = EVENT_CATALOG.get(event) or {
        "severity": "info",
        "description": "custom",
    }
    extra_c = _clean_extra(extra)
    consumer = str(extra_c.get("consumer") or extra_c.get("agent") or "")[:64]
    protection = extra_c.get("protection")
    if not protection and isinstance(extra_c.get("limits"), dict):
        protection = extra_c["limits"].get("protection")
    now = time.time()
    return {
        "schema_version": SCHEMA_VERSION,
        "service": "tollgate",
        "version": _version(),
        "event": str(event)[:64],
        "severity": meta.get("severity") or "info",
        "description": meta.get("description") or "",
        "provider": str(provider or "")[:64],
        "consumer": consumer,
        "protection": protection,
        "message": str(message or "")[:500],
        "ts": now,
        "iso": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
        "extra": extra_c,
    }


def maybe_alert(
    event: str,
    *,
    provider: str = "",
    message: str = "",
    extra: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    POST structured alert to webhook if configured.

    Rate-limited per (event, provider, consumer) to 1 / 5 min unless force=True.
    """
    url = _webhook_url()
    if not url:
        return {"ok": False, "skipped": True, "reason": "no webhook configured"}

    payload = build_alert_payload(
        event, provider=provider, message=message, extra=extra
    )
    cid = str(payload.get("consumer") or "")
    key = f"{event}:{provider}:{cid}"
    now = time.time()
    if not force and (now - _LAST.get(key, 0.0)) < _MIN_INTERVAL_S:
        return {"ok": False, "skipped": True, "reason": "rate_limited", "event": event}

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": f"Tollgate/{_version()} alerts",
            "X-Tollgate-Event": str(event)[:64],
            "X-Tollgate-Severity": str(payload.get("severity") or "info")[:16],
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            _LAST[key] = now
            return {
                "ok": True,
                "status": resp.getcode(),
                "event": event,
                "payload": payload,
            }
    except urllib.error.HTTPError as e:
        _LAST[key] = now
        return {"ok": False, "status": e.code, "error": str(e), "event": event}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e), "event": event}


def test_webhook(*, message: str = "tollgate alert test") -> dict[str, Any]:
    """Force-send webhook_test event (ignores rate limit)."""
    url = _webhook_url()
    if not url:
        return {
            "ok": False,
            "error": "no webhook configured",
            "hint": "set TOLLGATE_ALERT_WEBHOOK or cost_guard.alert_webhook_url",
        }
    return maybe_alert(
        "webhook_test",
        provider="",
        message=message or "tollgate alert test",
        extra={"probe": True},
        force=True,
    )


def clear_alert_cache() -> None:
    _LAST.clear()
