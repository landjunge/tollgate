"""Proactive budget alerts (webhook) — soft warn before hard deny."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from tollgate.app_config import load_config

# de-dupe: don't spam the same key more than once per interval
_LAST: dict[str, float] = {}
_MIN_INTERVAL_S = 300.0


def _webhook_url() -> str:
    env = (os.environ.get("TOLLGATE_ALERT_WEBHOOK") or "").strip()
    if env:
        return env
    guard = (load_config().get("cost_guard") or {})
    return str(guard.get("alert_webhook_url") or "").strip()


def maybe_alert(
    event: str,
    *,
    provider: str = "",
    message: str = "",
    extra: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    POST JSON to cost_guard.alert_webhook_url if set.

    Events: soft_budget, hard_deny, high_risk_block, circuit_open
    Rate-limited per (event, provider) to 1 / 5 min unless force=True.
    """
    url = _webhook_url()
    if not url:
        return {"ok": False, "skipped": True, "reason": "no webhook configured"}
    key = f"{event}:{provider}"
    now = time.time()
    if not force and (now - _LAST.get(key, 0.0)) < _MIN_INTERVAL_S:
        return {"ok": False, "skipped": True, "reason": "rate_limited"}
    body = {
        "service": "tollgate",
        "event": event,
        "provider": provider,
        "message": message,
        "ts": now,
        **(extra or {}),
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Tollgate/0.1 alerts",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            _LAST[key] = now
            return {"ok": True, "status": resp.getcode(), "event": event}
    except urllib.error.HTTPError as e:
        _LAST[key] = now
        return {"ok": False, "status": e.code, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


def clear_alert_cache() -> None:
    _LAST.clear()
