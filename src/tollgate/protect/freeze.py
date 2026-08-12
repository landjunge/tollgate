"""Protect freeze surface (re-export — logic stays in tollgate.freeze)."""

from __future__ import annotations

from tollgate.freeze import (
    allow_system_when_frozen,
    freeze_status,
    is_frozen,
    set_frozen,
)

__all__ = [
    "allow_system_when_frozen",
    "freeze_status",
    "is_frozen",
    "set_frozen",
]
