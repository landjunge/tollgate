"""
Accounting axis — ledger / usage / cost recording.

Facade over usage_ledger. Protect decides; Accounting records.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "consumer_usage",
    "provider_usage",
    "record_usage",
    "try_reserve_day_call",
    "usage_summary",
]


def try_reserve_day_call(
    provider: str,
    *,
    consumer: str = "",
    op: str = "call",
) -> dict[str, Any]:
    from tollgate.usage_ledger import try_reserve_day_call as _fn

    return _fn(provider, consumer=consumer, op=op)


def record_usage(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from tollgate.usage_ledger import record_usage as _fn

    return _fn(*args, **kwargs)


def usage_summary(*, root: Any = None) -> dict[str, Any]:
    from tollgate.usage_ledger import usage_summary as _fn

    return _fn(root=root) if root is not None else _fn()


def provider_usage(provider_id: str, **kwargs: Any) -> dict[str, Any]:
    from tollgate.usage_ledger import provider_usage as _fn

    return _fn(provider_id, **kwargs)


def consumer_usage(consumer: str, **kwargs: Any) -> dict[str, Any]:
    from tollgate.usage_ledger import consumer_usage as _fn

    return _fn(consumer, **kwargs)
