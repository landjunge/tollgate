"""
Prove availability gate (Phase 3).

Facade over chaos inject / gradual recovery so gateway/router do not import
chaos internals. Fail-closed if the subsystem errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Availability:
    """Whether a provider may receive traffic right now."""

    available: bool
    chaos: bool = False
    recovery: bool = False
    error: str = ""
    subsystem_error: bool = False

    def as_deny_dict(self, *, provider: str, op: str = "") -> dict[str, Any]:
        if self.available:
            return {"ok": True}
        if self.subsystem_error:
            return {
                "ok": False,
                "error": self.error or "chaos/protection check failed — fail-closed",
                "error_class": "PROVIDER_DOWN",
                "provider": provider,
                "op": op,
                "protection_error": True,
            }
        return {
            "ok": False,
            "error": self.error
            or (
                f"chaos inject: provider {provider} simulated unavailable"
                if self.chaos
                else f"gradual recovery: provider {provider} not yet fully restored"
            ),
            "error_class": "PROVIDER_DOWN",
            "provider": provider,
            "op": op,
            "chaos": self.chaos,
            "recovery": self.recovery,
        }


def is_provider_unavailable(provider: str) -> bool:
    """Re-export for call sites that only need a boolean."""
    from tollgate.chaos import is_provider_unavailable as _fn

    return bool(_fn(provider))


def is_provider_in_chaos(provider: str) -> bool:
    from tollgate.chaos import is_provider_in_chaos as _fn

    return bool(_fn(provider))


def check_provider_available(provider: str) -> Availability:
    """
    Production gate used by gateway + router.

    On any exception: fail-closed (unavailable, subsystem_error=True).
    """
    try:
        from tollgate.chaos import is_provider_in_chaos, is_provider_unavailable

        if not is_provider_unavailable(provider):
            return Availability(available=True)
        chaos = bool(is_provider_in_chaos(provider))
        return Availability(
            available=False,
            chaos=chaos,
            recovery=not chaos,
            error=(
                f"chaos inject: provider {provider} simulated unavailable"
                if chaos
                else f"gradual recovery: provider {provider} not yet fully restored"
            ),
        )
    except Exception as e:  # noqa: BLE001
        return Availability(
            available=False,
            subsystem_error=True,
            error=f"chaos/protection check failed — fail-closed ({e})",
        )
