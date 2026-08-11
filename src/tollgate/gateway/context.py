"""Request identity for attribution + request class."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import time
import uuid


class RequestClass(str, Enum):
    INTERACTIVE = "interactive"
    BATCH = "batch"
    FREE = "free"
    SYSTEM = "system"  # probes, auto_update — preferably non-billable


@dataclass
class RequestContext:
    """Mandatory metadata for every gateway call (when known)."""

    agent_id: str = ""
    job_id: str = ""
    session_id: str = ""
    # Consumer lane (n8n / gnom / …) — used for envelopes + ledger attribution
    consumer: str = ""
    request_class: RequestClass = RequestClass.INTERACTIVE
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    allow_paid_fallback: bool = False
    billable: bool = True
    created_ts: float = field(default_factory=time.time)

    def consumer_id(self) -> str:
        """Prefer explicit consumer; fall back to agent_id for desk paths."""
        c = (self.consumer or "").strip()
        if c:
            return c[:64]
        a = (self.agent_id or "").strip()
        if a.startswith("openai:"):
            a = a[7:]
        return (a or "anonymous")[:64]

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "job_id": self.job_id,
            "session_id": self.session_id,
            "consumer": self.consumer_id(),
            "request_class": self.request_class.value,
            "request_id": self.request_id,
            "allow_paid_fallback": self.allow_paid_fallback,
            "billable": self.billable,
        }

    @classmethod
    def system(cls, **kw: Any) -> "RequestContext":
        return cls(
            request_class=RequestClass.SYSTEM,
            billable=False,
            agent_id=kw.get("agent_id") or "system",
            **{k: v for k, v in kw.items() if k not in ("agent_id", "request_class", "billable")},
        )

    @classmethod
    def free(cls, **kw: Any) -> "RequestContext":
        return cls(request_class=RequestClass.FREE, allow_paid_fallback=False, **kw)
