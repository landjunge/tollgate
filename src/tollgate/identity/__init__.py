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
    from tollgate.consumers import normalize_consumer_id

    return normalize_consumer_id(consumer or agent_id)


def consumer_envelope(consumer: str) -> dict[str, Any]:
    from tollgate.limits import consumer_envelope as _env

    return _env(consumer)


def list_consumers() -> list[Any]:
    try:
        from tollgate.consumers import list_consumers as _list

        return list(_list() or [])
    except Exception as e:  # noqa: BLE001
        from tollgate.soft_fail import soft_fail

        soft_fail("identity_list", e)
        return []
