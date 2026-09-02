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
import re
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


# Consumer secrets are hashed with salted scrypt from the standard library.
#
# Auto-generated secrets carry 192 bits, so a plain digest would already be out
# of reach. Operator-chosen secrets (`consumer-add --secret`) are the reason for
# this: an unsalted single-round SHA-256 of a human-picked string falls to a
# wordlist the moment consumers.json is read by anything else on the box.
#
# n=2**14 keeps `verify_consumer` at roughly a millisecond, which is affordable
# on a request path that also does network I/O.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_PREFIX = "scrypt$"

# Advisory only. Salted scrypt is what actually protects a stored secret; this
# threshold exists so `consumer-add --secret hunter2` says something out loud
# instead of succeeding silently. It deliberately does not refuse: the operator
# asked for that secret, and breaking existing desks to enforce a style rule
# would be the wrong trade.
WEAK_CUSTOM_SECRET_LEN = 16


def _scrypt_hash(secret: str, salt: bytes) -> str:
    digest = hashlib.scrypt(
        secret.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32
    )
    return f"{_SCRYPT_PREFIX}{salt.hex()}${digest.hex()}"


def hash_consumer_secret(secret: str) -> str:
    return _scrypt_hash(secret, secrets.token_bytes(16))


def verify_consumer_secret(secret: str, stored: str) -> bool:
    """Constant-time check against either hash format.

    Files written before the scrypt change hold a bare SHA-256 hex digest. Those
    keep working so an upgrade never locks a desk out of its own consumers; they
    are re-hashed on the next `consumer-add` for that id.
    """
    stored = (stored or "").strip()
    if stored.startswith(_SCRYPT_PREFIX):
        try:
            salt_hex, digest_hex = stored[len(_SCRYPT_PREFIX) :].split("$", 1)
            salt = bytes.fromhex(salt_hex)
        except ValueError:
            return False
        computed = _scrypt_hash(secret, salt)
        if len(computed) != len(stored):
            return False
        return hmac.compare_digest(computed, stored)
    # Legacy: unsalted sha256.
    digest = _sha256(secret)
    if len(stored) != len(digest):
        return False
    return hmac.compare_digest(stored, digest)


def secret_hash_is_legacy(stored: str) -> bool:
    return not (stored or "").strip().startswith(_SCRYPT_PREFIX)


# A consumer id is client-asserted: it arrives in the X-Consumer-Key header and,
# in open mode, any label is accepted. It then flows into the usage ledger, into
# GET /v1/control, and from there into the dashboard DOM. Without a charset it
# is an injection vector into the control plane's own UI, so it is constrained
# here — once, at the edge — rather than at each of the places that render it.
CONSUMER_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")

ANONYMOUS = "anonymous"


def normalize_consumer_id(value: str | None) -> str:
    """Canonical consumer id, or ``anonymous`` when the label is unusable.

    Rejecting rather than sanitizing is deliberate: a silently stripped label
    would silently split one lane's budget across two ledger keys.
    """
    cid = (value or "").strip()[:64]
    if not cid or cid in (ANONYMOUS, "*"):
        return ANONYMOUS
    if CONSUMER_ID_RE.fullmatch(cid) is None:
        return ANONYMOUS
    return cid


def consumer_id_is_valid(value: str | None) -> bool:
    cid = (value or "").strip()
    return bool(cid) and CONSUMER_ID_RE.fullmatch(cid) is not None


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
                raise ValueError("consumers.json is not an object")
        except Exception as e:  # noqa: BLE001
            from tollgate.soft_fail import soft_fail

            # File exists but is unreadable — never treat as open/no-auth.
            soft_fail("consumers_parse", e)
            raw = {"version": 1, "consumers": [], "_corrupt": True}
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
        if not cid or not sh or not consumer_id_is_valid(cid):
            continue
        out.append(
            Consumer(
                id=cid,
                secret_hash=sh,
                admin=bool(row.get("admin")),
                enabled=bool(row.get("enabled", True)),
                label=str(row.get("label") or ""),
            )
        )
    return out


def consumers_corrupt() -> bool:
    """True when consumers.json exists but could not be parsed."""
    return bool(_load_raw().get("_corrupt"))


_PUBLIC_BIND_HOSTS = frozenset({"0.0.0.0", "::", "[::]", "*"})


def is_public_bind(host: str | None = None) -> bool:
    """True when HOST would listen on all interfaces (docker -p / 0.0.0.0)."""
    h = (host if host is not None else os.environ.get("HOST") or "127.0.0.1").strip()
    return h in _PUBLIC_BIND_HOSTS


def allow_open_public() -> bool:
    return (os.environ.get("TOLLGATE_ALLOW_OPEN_PUBLIC") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def open_public_bind_error(*, host: str | None = None) -> str | None:
    """
    Product rule: localhost + open mode is OK.
    Public bind + open mode is refused unless TOLLGATE_ALLOW_OPEN_PUBLIC=1.
    """
    if auth_required():
        return None
    if not is_public_bind(host):
        return None
    if allow_open_public():
        return None
    h = (host if host is not None else os.environ.get("HOST") or "127.0.0.1").strip()
    return (
        f"refusing open mode on public bind {h} — "
        "use HOST=127.0.0.1, or: tollgate consumer-add desk --admin, "
        "or set TOLLGATE_ALLOW_OPEN_PUBLIC=1"
    )


def refuse_open_public_bind(*, host: str | None = None) -> None:
    msg = open_public_bind_error(host=host)
    if msg:
        raise RuntimeError(msg)


def auth_required() -> bool:
    if (os.environ.get("TOLLGATE_REQUIRE_AUTH") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return True
    if consumers_corrupt():
        return True
    return any(c.enabled for c in list_consumers())


def parse_consumer_header(
    x_consumer_key: str | None,
    x_consumer_id: str | None = None,
) -> tuple[str, str]:
    raw = (x_consumer_key or "").strip()
    cid_h = (x_consumer_id or "").strip()
    if not raw and not cid_h:
        return ANONYMOUS, ""
    if ":" in raw and not cid_h:
        left, right = raw.split(":", 1)
        return normalize_consumer_id(left), right.strip()
    if cid_h:
        return normalize_consumer_id(cid_h), raw
    if auth_required():
        return ANONYMOUS, raw
    return normalize_consumer_id(raw), ""


def verify_consumer(
    x_consumer_key: str | None,
    x_consumer_id: str | None = None,
    *,
    need_admin: bool = False,
) -> dict[str, Any]:
    cid, secret = parse_consumer_header(x_consumer_key, x_consumer_id)
    if consumers_corrupt():
        return {
            "ok": False,
            "consumer": cid,
            "admin": False,
            "mode": "auth",
            "error": "consumers.json corrupt — fail-closed (fix JSON or consumer-add)",
        }
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
    matched: Consumer | None = None
    for c in list_consumers():
        if not c.enabled:
            continue
        if not verify_consumer_secret(secret, c.secret_hash):
            continue
        # Secret match authenticates the *stored* id, not the claimed one.
        # `desk:n8n_secret` therefore becomes n8n. Not a privilege gain (you
        # already hold n8n's secret); left unchanged because callers may rely
        # on it. Do not treat the header id as the authenticated principal.
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
    if not cid or cid == ANONYMOUS or not consumer_id_is_valid(cid):
        return {
            "ok": False,
            "error": "invalid consumer id (allowed: letters, digits, . _ - : up to 64 chars)",
        }
    plain = secret or secrets.token_urlsafe(24)
    warning = None
    if secret is not None and len(secret) < WEAK_CUSTOM_SECRET_LEN:
        warning = (
            f"custom secret is shorter than {WEAK_CUSTOM_SECRET_LEN} characters — "
            "omit --secret to have a strong one generated"
        )
    path = consumers_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        raw = _load_raw()
        rows = [r for r in (raw.get("consumers") or []) if not (isinstance(r, dict) and r.get("id") == cid)]
        rows.append(
            {
                "id": cid,
                "secret_hash": hash_consumer_secret(plain),
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
    out: dict[str, Any] = {
        "ok": True,
        "id": cid,
        "secret": plain,
        "admin": admin,
        "path": str(path),
        "note": "store secret now — only a salted hash is kept on disk",
    }
    if warning:
        out["warning"] = warning
    return out


def auth_status() -> dict[str, Any]:
    cs = list_consumers()
    corrupt = consumers_corrupt()
    return {
        "required": auth_required(),
        "consumers_n": len(cs),
        "consumers": [
            {"id": c.id, "admin": c.admin, "enabled": c.enabled, "label": c.label}
            for c in cs
        ],
        "path": str(consumers_path()),
        "corrupt": corrupt,
    }
