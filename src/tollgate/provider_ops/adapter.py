"""
ProviderAdapter protocol (M9 target shape).

Concrete modules (deepseek, openrouter, …) stay free-form.
Registry binds them; later adapters can wrap modules 1:1.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProviderAdapter(Protocol):
    """Uniform surface Tollgate expects — implementations may differ."""

    id: str

    def status(self, **kwargs: Any) -> dict[str, Any]:
        """Health / readiness card fragment."""
        ...

    def execute(self, op: str, **kwargs: Any) -> Any:
        """Run named op (chat, search, budget, …)."""
        ...
