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


def query_audit(**kwargs: Any) -> list[dict[str, Any]]:
    try:
        from tollgate.audit_log import query_audit as _fn

        return list(_fn(**kwargs) or [])
    except Exception:  # noqa: BLE001
        try:
            from tollgate.audit_log import read_audit as _fn

            return list(_fn(**kwargs) or [])
        except Exception:  # noqa: BLE001
            return []
