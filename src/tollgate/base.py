"""Shared helpers for the keys module (masking, env access)."""

from __future__ import annotations

import os
from typing import Any

from tollgate.secrets import is_usable_api_key


def get_env(*names: str, default: str = "") -> str:
    """First non-empty env value among names."""
    for n in names:
        v = (os.environ.get(n) or "").strip()
        if v:
            return v
    return default


def mask_secret(value: str | None, *, keep: int = 4) -> str:
    """Show only last `keep` chars (or empty/missing markers)."""
    s = (value or "").strip()
    if not s:
        return ""
    if not is_usable_api_key(s):
        return "(placeholder)"
    if len(s) <= keep:
        return "*" * len(s)
    return f"…{s[-keep:]}"


def key_present(name: str) -> bool:
    return is_usable_api_key(os.environ.get(name))


def as_status(
    *,
    id: str,
    ready: bool,
    detail: dict[str, Any] | None = None,
    error: str | None = None,
    masked: dict[str, str] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": id,
        "ready": ready,
        "ok": ready and not error,
    }
    if error:
        out["error"] = error
    if masked:
        out["keys"] = masked
    if detail:
        out["detail"] = detail
    return out
