"""
Multi-consumer identity for HTTP /v1.

Desk / USB open mode:
  - No consumers.json entries and TOLLGATE_REQUIRE_AUTH unset → open.

Auth mode:
  - User/consumers.json has entries OR TOLLGATE_REQUIRE_AUTH=1
  - Header: X-Consumer-Key: <id>:<secret>
  - Or: X-Consumer-Id + X-Consumer-Key: <secret>

Secrets stored only as sha256 hashes on disk.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tollgate.paths import user_dir

_LOCK = threading.RLock()
_CACHE: dict[str, Any] | None = None
_CACHE_MTIME: float | None = None


@dataclass(frozen=True)
class Consumer:
    id: str
    secret_hash: str
    admin: bool = False
    enabled: bool = True
    label: str = ""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def consumers_path() -> Path:
    env = (os.environ.get("TOLLGATE_CONSUMERS") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (user_dir() / "consumers.json").resolve()


def _load_raw() -> dict[str, Any]:
    global _CACHE, _CACHE_MTIME
    path = consumers_path()
    with _LOCK:
        mtime = path.stat().st_mtime if path.is_file() else None
        if _CACHE is not None and mtime is not None and mtime == _CACHE_MTIME:
            return dict(_CACHE)
        if not path.is_file():
            _CACHE = {"version": 1, "consumers": []}
            _CACHE_MTIME = mtime
            return dict(_CACHE)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raw = {"version": 1, "consumers": []}
        except Exception:  # noqa: BLE001
            raw = {"version": 1, "consumers": []}
        _CACHE = raw
        _CACHE_MTIME = mtime
        return dict(raw)


def clear_cache() -> None:
    global _CACHE, _CACHE_MTIME
    with _LOCK:
        _CACHE = None
        _CACHE_MTIME = None


def list_consumers() -> list[Consumer]:
    raw = _load_raw()
    out: list[Consumer] = []
    for row in raw.get("consumers") or []:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("id") or "").strip()
        sh = str(row.get("secret_hash") or "").strip()
        if not cid or not sh:
            continue
        out.append(
            Consumer(
                id=cid[:64],
                secret_hash=sh,
                admin=bool(row.get("admin")),
                enabled=bool(row.get("enabled", True)),
                label=str(row.get("label") or ""),
            )
        )
    return out


def auth_required() -> bool:
    if (os.environ.get("TOLLGATE_REQUIRE_AUTH") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return True
    return any(c.enabled for c in list_consumers())


def parse_consumer_header(
    x_consumer_key: str | None,
    x_consumer_id: str | None = None,
) -> tuple[str, str]:
    raw = (x_consumer_key or "").strip()
    cid_h = (x_consumer_id or "").strip()
    if not raw and not cid_h:
        return "anonymous", ""
    if ":" in raw and not cid_h:
        left, right = raw.split(":", 1)
        return (left.strip()[:64] or "anonymous"), right.strip()
    if cid_h:
        return cid_h[:64], raw
    if auth_required():
        return "anonymous", raw
    return (raw[:64] or "anonymous"), ""


def verify_consumer(
    x_consumer_key: str | None,
    x_consumer_id: str | None = None,
    *,
    need_admin: bool = False,
) -> dict[str, Any]:
    cid, secret = parse_consumer_header(x_consumer_key, x_consumer_id)
    if not auth_required():
        return {
            "ok": True,
            "consumer": cid or "anonymous",
            "admin": True,
            "mode": "open",
        }
    if not secret:
        return {
            "ok": False,
            "consumer": cid,
            "admin": False,
            "mode": "auth",
            "error": "missing consumer secret (use X-Consumer-Key: id:secret)",
        }
    digest = _sha256(secret)
    matched: Consumer | None = None
    for c in list_consumers():
        if not c.enabled:
            continue
        if not hmac.compare_digest(c.secret_hash, digest):
            continue
        # secret matches — prefer id match, else accept hash match
        if cid in ("", "anonymous") or c.id == cid:
            matched = c
            break
        if matched is None:
            matched = c
    if matched is None:
        return {
            "ok": False,
            "consumer": cid,
            "admin": False,
            "mode": "auth",
            "error": "invalid consumer credentials",
        }
    if need_admin and not matched.admin:
        return {
            "ok": False,
            "consumer": matched.id,
            "admin": False,
            "mode": "auth",
            "error": "admin scope required",
        }
    return {
        "ok": True,
        "consumer": matched.id,
        "admin": matched.admin,
        "mode": "auth",
    }


def add_consumer(
    consumer_id: str,
    *,
    secret: str | None = None,
    admin: bool = False,
    label: str = "",
) -> dict[str, Any]:
    cid = (consumer_id or "").strip()[:64]
    if not cid or cid == "anonymous":
        return {"ok": False, "error": "invalid consumer id"}
    plain = secret or secrets.token_urlsafe(24)
    path = consumers_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        raw = _load_raw()
        rows = [r for r in (raw.get("consumers") or []) if not (isinstance(r, dict) and r.get("id") == cid)]
        rows.append(
            {
                "id": cid,
                "secret_hash": _sha256(plain),
                "admin": bool(admin),
                "enabled": True,
                "label": label or cid,
            }
        )
        raw = {"version": 1, "consumers": rows}
        path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
        global _CACHE, _CACHE_MTIME
        _CACHE = raw
        _CACHE_MTIME = path.stat().st_mtime
    return {
        "ok": True,
        "id": cid,
        "secret": plain,
        "admin": admin,
        "path": str(path),
        "note": "store secret now — only the hash is kept on disk",
    }


def auth_status() -> dict[str, Any]:
    cs = list_consumers()
    return {
        "required": auth_required(),
        "consumers_n": len(cs),
        "consumers": [
            {"id": c.id, "admin": c.admin, "enabled": c.enabled, "label": c.label}
            for c in cs
        ],
        "path": str(consumers_path()),
    }
