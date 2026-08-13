"""
Audit axis — append-only ops trail.

Facade over audit_log. Never mutates policy decisions.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "append_audit",
    "query_audit",
]


def append_audit(event: str, **kwargs: Any) -> None:
    from tollgate.audit_log import append_audit as _fn

    _fn(event, **kwargs)


def query_audit(**kwargs: Any) -> dict[str, Any]:
    """Pass-through to audit_log.query_audit (dict with events). No read_audit."""
    try:
        from tollgate.audit_log import query_audit as _fn

        out = _fn(**kwargs)
        if isinstance(out, dict):
            return out
        return {"ok": True, "events": list(out or []), "count": len(list(out or []))}
    except Exception as e:  # noqa: BLE001
        from tollgate.soft_fail import soft_fail

        soft_fail("audit_query", e)
        return {"ok": False, "events": [], "count": 0, "error": str(e)}
