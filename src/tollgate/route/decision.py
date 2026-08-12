"""
RouteDecision — where should this request run? (not execution)

route() builds this; execute_routed consumes the dict form for API stability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RouteDecision:
    ok: bool
    provider: str = ""
    model: str = ""
    intent: str = ""
    prefer_free: bool = False
    free_only: bool = False
    reason: str = ""
    error: str = ""
    tried: list[dict[str, Any]] = field(default_factory=list)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Public shape expected by OpenAI path / service.route / chaos."""
        out: dict[str, Any] = {
            "ok": self.ok,
            "prefer_free": self.prefer_free,
            "free_only": self.free_only,
            "tried": list(self.tried),
            "error": self.error or None,
        }
        if self.ok and self.provider:
            out["route"] = {
                "provider": self.provider,
                "model": self.model,
                "intent": self.intent,
            }
            out["provider"] = self.provider
            out["model"] = self.model
        else:
            out["route"] = None
        if self.candidates:
            out["candidates"] = list(self.candidates)
        if self.reason:
            out["reason"] = self.reason
        for k, v in self.extra.items():
            out.setdefault(k, v)
        return out
