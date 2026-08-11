"""
Agent protection — stop runaway loops before they become invoices.

Tracks per-consumer short windows (minute / hour) on disk so multi-worker
desks share limits. Day caps stay in the usage ledger.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from tollgate.filelock import FileLock
from tollgate.paths import user_dir

_LOCK = threading.RLock()
RATES_NAME = "agent_rates.json"


def rates_path(root: Path | None = None) -> Path:
    return (user_dir(root) / RATES_NAME).resolve()


def _minute_bucket(ts: float | None = None) -> str:
    dt = datetime.fromtimestamp(ts or time.time())
    return dt.strftime("%Y-%m-%dT%H:%M")


def _hour_bucket(ts: float | None = None) -> str:
    dt = datetime.fromtimestamp(ts or time.time())
    return dt.strftime("%Y-%m-%dT%H")


def _empty() -> dict[str, Any]:
    return {"version": 1, "consumers": {}}


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return _empty()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return _empty()
        raw.setdefault("consumers", {})
        return raw
    except Exception:  # noqa: BLE001
        return _empty()


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _slot(row: dict[str, Any], kind: str, bucket: str) -> dict[str, Any]:
    key = "minute" if kind == "minute" else "hour"
    cur = row.get(key)
    if not isinstance(cur, dict) or cur.get("bucket") != bucket:
        cur = {"bucket": bucket, "requests": 0, "usd": 0.0, "tokens": 0}
        row[key] = cur
    return cur


def peek_rates(consumer: str, *, root: Path | None = None) -> dict[str, Any]:
    """Read-only current minute/hour counters for a consumer."""
    cid = (consumer or "anonymous").strip()[:64] or "anonymous"
    path = rates_path(root)
    with _LOCK:
        with FileLock(path):
            data = _load(path)
            row = dict((data.get("consumers") or {}).get(cid) or {})
    mb, hb = _minute_bucket(), _hour_bucket()
    minute = row.get("minute") if isinstance(row.get("minute"), dict) else {}
    hour = row.get("hour") if isinstance(row.get("hour"), dict) else {}
    return {
        "consumer": cid,
        "minute": {
            "bucket": mb,
            "requests": int(minute.get("requests") or 0) if minute.get("bucket") == mb else 0,
            "usd": float(minute.get("usd") or 0) if minute.get("bucket") == mb else 0.0,
        },
        "hour": {
            "bucket": hb,
            "requests": int(hour.get("requests") or 0) if hour.get("bucket") == hb else 0,
            "usd": float(hour.get("usd") or 0) if hour.get("bucket") == hb else 0.0,
            "tokens": int(hour.get("tokens") or 0) if hour.get("bucket") == hb else 0,
        },
    }


def record_attempt(
    consumer: str,
    *,
    tokens_est: int = 0,
    usd_est: float = 0.0,
    root: Path | None = None,
) -> dict[str, Any]:
    """
    Count one admitted attempt against minute/hour windows.

    Called after protection checks pass (so blocked requests do not burn quota).
    """
    cid = (consumer or "anonymous").strip()[:64] or "anonymous"
    path = rates_path(root)
    tok = max(0, int(tokens_est or 0))
    usd = max(0.0, float(usd_est or 0.0))
    with _LOCK:
        with FileLock(path):
            data = _load(path)
            consumers = data.setdefault("consumers", {})
            row = consumers.get(cid) if isinstance(consumers.get(cid), dict) else {}
            row = dict(row)
            m = _slot(row, "minute", _minute_bucket())
            h = _slot(row, "hour", _hour_bucket())
            m["requests"] = int(m.get("requests") or 0) + 1
            m["usd"] = float(m.get("usd") or 0.0) + usd
            m["tokens"] = int(m.get("tokens") or 0) + tok
            h["requests"] = int(h.get("requests") or 0) + 1
            h["usd"] = float(h.get("usd") or 0.0) + usd
            h["tokens"] = int(h.get("tokens") or 0) + tok
            consumers[cid] = row
            data["updated_at"] = time.time()
            _write(path, data)
            return {"ok": True, "consumer": cid, "minute": m, "hour": h}


def estimate_request_usd(tokens_est: int, *, usd_hint: float = 0.0) -> float:
    """Rough pre-admit $ estimate when provider rate unknown."""
    if usd_hint > 0:
        return float(usd_hint)
    # ~$0.50 / 1M tokens blended conservative for free-first desks
    return max(0.0, int(tokens_est or 0) / 1_000_000.0 * 0.5)
