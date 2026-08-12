"""
Identity axis — who is calling?

Facade over consumers / agent_id resolution. No budget logic here.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "consumer_envelope",
    "list_consumers",
    "normalize_consumer",
]


def normalize_consumer(consumer: str | None, agent_id: str | None = None) -> str:
    """Canonical consumer id for admit / ledger / audit."""
    c = (consumer or agent_id or "").strip()[:64]
    return c or "anonymous"


def consumer_envelope(consumer: str) -> dict[str, Any]:
    from tollgate.limits import consumer_envelope as _env

    return _env(consumer)


def list_consumers() -> list[Any]:
    try:
        from tollgate.consumers import list_consumers as _list

        return list(_list() or [])
    except Exception:  # noqa: BLE001
        return []
