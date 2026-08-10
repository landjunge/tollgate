"""
Circuit breaker per (provider, model, key_ref).

Prevents thundering herd and cascading failures (Portkey/LiteLLM pattern).
"""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CircuitState(str, Enum):
    CLOSED = "closed"  # normal
    OPEN = "open"  # fail fast
    HALF_OPEN = "half_open"  # single canary


@dataclass
class Circuit:
    provider: str
    model: str = ""
    key_ref: str = ""
    state: CircuitState = CircuitState.CLOSED
    failures: int = 0
    successes: int = 0
    opened_at: float = 0.0
    cooldown_s: float = 30.0
    failure_threshold: int = 5
    half_open_successes_needed: int = 1
    last_error: str = ""

    @property
    def key(self) -> str:
        return f"{self.provider}|{self.model or '*'}|{self.key_ref or '*'}"

    def allow(self) -> bool:
        now = time.time()
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            # jittered cooldown
            wait = self.cooldown_s * (0.8 + 0.4 * random.random())
            if now - self.opened_at >= wait:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        # half-open: allow one canary (caller must report)
        return True

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.half_open_successes_needed:
                self.state = CircuitState.CLOSED
                self.failures = 0
                self.successes = 0
        else:
            self.failures = max(0, self.failures - 1)

    def record_failure(self, *, message: str = "", hard: bool = False) -> None:
        self.last_error = (message or "")[:200]
        self.failures += 1
        self.successes = 0
        if hard or self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = time.time()
            if hard:
                # auth dead — long cooldown
                self.cooldown_s = max(self.cooldown_s, 300.0)

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "state": self.state.value,
            "failures": self.failures,
            "cooldown_s": self.cooldown_s,
            "opened_at": self.opened_at,
            "last_error": self.last_error,
        }


class CircuitRegistry:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._circuits: dict[str, Circuit] = {}

    def get(
        self,
        provider: str,
        *,
        model: str = "",
        key_ref: str = "",
    ) -> Circuit:
        k = f"{provider}|{model or '*'}|{key_ref or '*'}"
        with self._lock:
            if k not in self._circuits:
                self._circuits[k] = Circuit(
                    provider=provider, model=model, key_ref=key_ref
                )
            return self._circuits[k]

    def allow(self, provider: str, *, model: str = "", key_ref: str = "") -> bool:
        return self.get(provider, model=model, key_ref=key_ref).allow()

    def success(self, provider: str, *, model: str = "", key_ref: str = "") -> None:
        with self._lock:
            self.get(provider, model=model, key_ref=key_ref).record_success()

    def failure(
        self,
        provider: str,
        *,
        model: str = "",
        key_ref: str = "",
        message: str = "",
        hard: bool = False,
    ) -> None:
        with self._lock:
            self.get(provider, model=model, key_ref=key_ref).record_failure(
                message=message, hard=hard
            )

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [c.as_dict() for c in self._circuits.values()]


_CIRCUITS: CircuitRegistry | None = None


def get_circuits() -> CircuitRegistry:
    global _CIRCUITS
    if _CIRCUITS is None:
        _CIRCUITS = CircuitRegistry()
    return _CIRCUITS
