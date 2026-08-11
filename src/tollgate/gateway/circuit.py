"""
Circuit breaker per (provider, model, key_ref).

Prevents thundering herd and cascading failures (Portkey/LiteLLM pattern).

State is persisted under ``User/circuits.json`` with a cross-process file lock
so multi-worker uvicorn (and multiple consumers) share open/closed state.

Defaults (cooldown, threshold, jitter range) come from keys_app.json → circuits.
"""

from __future__ import annotations

import json
import random
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from tollgate.filelock import FileLock
from tollgate.paths import user_dir

CIRCUITS_NAME = "circuits.json"

# Fallback defaults when config is unavailable (must match app_config DEFAULT)
_DEFAULT_COOLDOWN_S = 30.0
_DEFAULT_HARD_COOLDOWN_S = 300.0
_DEFAULT_FAILURE_THRESHOLD = 5
_DEFAULT_HALF_OPEN_NEEDED = 1
_DEFAULT_JITTER_MIN = 0.8
_DEFAULT_JITTER_MAX = 1.2


class CircuitState(str, Enum):
    CLOSED = "closed"  # normal
    OPEN = "open"  # fail fast
    HALF_OPEN = "half_open"  # single canary


def _circuit_defaults() -> dict[str, Any]:
    """Live defaults from keys_app.json circuits block (safe fallbacks)."""
    try:
        from tollgate.app_config import load_config

        cfg = load_config() or {}
        c = cfg.get("circuits") or {}
        if not isinstance(c, dict):
            c = {}
    except Exception:  # noqa: BLE001
        c = {}

    jmin = float(c.get("jitter_min", _DEFAULT_JITTER_MIN))
    jmax = float(c.get("jitter_max", _DEFAULT_JITTER_MAX))
    # Safety: keep a usable range even if config is inverted/broken
    if jmin <= 0:
        jmin = _DEFAULT_JITTER_MIN
    if jmax <= 0:
        jmax = _DEFAULT_JITTER_MAX
    if jmin > jmax:
        jmin, jmax = jmax, jmin

    return {
        "cooldown_s": float(c.get("cooldown_s", _DEFAULT_COOLDOWN_S)),
        "hard_cooldown_s": float(c.get("hard_cooldown_s", _DEFAULT_HARD_COOLDOWN_S)),
        "failure_threshold": int(c.get("failure_threshold", _DEFAULT_FAILURE_THRESHOLD)),
        "half_open_successes_needed": int(
            c.get("half_open_successes_needed", _DEFAULT_HALF_OPEN_NEEDED)
        ),
        "jitter_min": jmin,
        "jitter_max": jmax,
    }


@dataclass
class Circuit:
    provider: str
    model: str = ""
    key_ref: str = ""
    state: CircuitState = CircuitState.CLOSED
    failures: int = 0
    successes: int = 0
    opened_at: float = 0.0
    cooldown_s: float = _DEFAULT_COOLDOWN_S
    hard_cooldown_s: float = _DEFAULT_HARD_COOLDOWN_S
    failure_threshold: int = _DEFAULT_FAILURE_THRESHOLD
    half_open_successes_needed: int = _DEFAULT_HALF_OPEN_NEEDED
    jitter_min: float = _DEFAULT_JITTER_MIN
    jitter_max: float = _DEFAULT_JITTER_MAX
    last_error: str = ""

    @property
    def key(self) -> str:
        return f"{self.provider}|{self.model or '*'}|{self.key_ref or '*'}"

    def _jitter_factor(self) -> float:
        """Multiplicative factor in [jitter_min, jitter_max] (clamped)."""
        lo = float(self.jitter_min)
        hi = float(self.jitter_max)
        if lo <= 0:
            lo = _DEFAULT_JITTER_MIN
        if hi <= 0:
            hi = _DEFAULT_JITTER_MAX
        if lo > hi:
            lo, hi = hi, lo
        if lo == hi:
            return lo
        return lo + (hi - lo) * random.random()

    def allow(self) -> bool:
        now = time.time()
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            wait = self.cooldown_s * self._jitter_factor()
            if now - self.opened_at >= wait:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.half_open_successes_needed:
                self.state = CircuitState.CLOSED
                self.failures = 0
                self.successes = 0
                # Hard failures elevate cooldown_s for *this* OPEN window only.
                # On recover, restore soft defaults so normal failures do not
                # permanently stick at hard_cooldown_s (persisted circuits.json).
                self._restore_soft_cooldown()
        else:
            self.failures = max(0, self.failures - 1)

    def _restore_soft_cooldown(self) -> None:
        """Reset cooldown fields from live keys_app defaults after CLOSE."""
        try:
            d = _circuit_defaults()
            self.cooldown_s = float(d["cooldown_s"])
            self.hard_cooldown_s = float(d["hard_cooldown_s"])
            self.failure_threshold = int(d["failure_threshold"])
            self.half_open_successes_needed = int(d["half_open_successes_needed"])
            self.jitter_min = float(d["jitter_min"])
            self.jitter_max = float(d["jitter_max"])
        except Exception:  # noqa: BLE001
            self.cooldown_s = _DEFAULT_COOLDOWN_S
            self.hard_cooldown_s = _DEFAULT_HARD_COOLDOWN_S

    def record_failure(self, *, message: str = "", hard: bool = False) -> None:
        try:
            from tollgate.redact import redact_secrets

            msg = redact_secrets(message or "")
        except Exception:  # noqa: BLE001
            msg = (message or "")[:200]
        self.last_error = msg[:200]
        self.failures += 1
        self.successes = 0
        if hard or self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = time.time()
            if hard:
                # Elevate cooldown for this OPEN period (AUTH_DEAD etc.).
                # Sticky only until successful half-open recovery (see record_success).
                self.cooldown_s = max(self.cooldown_s, float(self.hard_cooldown_s))

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "provider": self.provider,
            "model": self.model,
            "key_ref": self.key_ref,
            "state": self.state.value,
            "failures": self.failures,
            "successes": self.successes,
            "cooldown_s": self.cooldown_s,
            "hard_cooldown_s": self.hard_cooldown_s,
            "opened_at": self.opened_at,
            "failure_threshold": self.failure_threshold,
            "half_open_successes_needed": self.half_open_successes_needed,
            "jitter_min": self.jitter_min,
            "jitter_max": self.jitter_max,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Circuit:
        st = str(d.get("state") or "closed")
        try:
            state = CircuitState(st)
        except ValueError:
            state = CircuitState.CLOSED
        defaults = _circuit_defaults()
        jmin = float(d.get("jitter_min", defaults["jitter_min"]))
        jmax = float(d.get("jitter_max", defaults["jitter_max"]))
        if jmin <= 0:
            jmin = defaults["jitter_min"]
        if jmax <= 0:
            jmax = defaults["jitter_max"]
        if jmin > jmax:
            jmin, jmax = jmax, jmin
        return cls(
            provider=str(d.get("provider") or "unknown"),
            model=str(d.get("model") or ""),
            key_ref=str(d.get("key_ref") or ""),
            state=state,
            failures=int(d.get("failures") or 0),
            successes=int(d.get("successes") or 0),
            opened_at=float(d.get("opened_at") or 0.0),
            cooldown_s=float(d.get("cooldown_s") or defaults["cooldown_s"]),
            hard_cooldown_s=float(
                d.get("hard_cooldown_s") or defaults["hard_cooldown_s"]
            ),
            failure_threshold=int(
                d.get("failure_threshold") or defaults["failure_threshold"]
            ),
            half_open_successes_needed=int(
                d.get("half_open_successes_needed")
                or defaults["half_open_successes_needed"]
            ),
            jitter_min=jmin,
            jitter_max=jmax,
            last_error=str(d.get("last_error") or "")[:200],
        )


def circuits_path(root: Path | None = None) -> Path:
    return (user_dir(root) / CIRCUITS_NAME).resolve()


class CircuitRegistry:
    def __init__(self, *, root: Path | None = None, persist: bool = True) -> None:
        self._lock = threading.RLock()
        self._circuits: dict[str, Circuit] = {}
        self._root = root
        self._persist = persist
        if persist:
            self._load()

    def _path(self) -> Path:
        return circuits_path(self._root)

    def _load(self) -> None:
        path = self._path()
        if not path.is_file():
            return
        try:
            with FileLock(path):
                raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return
        if not isinstance(raw, dict):
            return
        items = raw.get("circuits") or []
        if not isinstance(items, list):
            return
        with self._lock:
            for row in items:
                if not isinstance(row, dict):
                    continue
                c = Circuit.from_dict(row)
                self._circuits[c.key] = c

    def _save_unlocked(self) -> None:
        if not self._persist:
            return
        path = self._path()
        payload = {
            "version": 1,
            "updated_at": time.time(),
            "circuits": [c.as_dict() for c in self._circuits.values()],
        }
        try:
            with FileLock(path):
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".json.tmp")
                tmp.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                tmp.replace(path)
        except Exception:  # noqa: BLE001
            pass

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
                d = _circuit_defaults()
                self._circuits[k] = Circuit(
                    provider=provider,
                    model=model,
                    key_ref=key_ref,
                    cooldown_s=d["cooldown_s"],
                    hard_cooldown_s=d["hard_cooldown_s"],
                    failure_threshold=d["failure_threshold"],
                    half_open_successes_needed=d["half_open_successes_needed"],
                    jitter_min=d["jitter_min"],
                    jitter_max=d["jitter_max"],
                )
            return self._circuits[k]

    def allow(self, provider: str, *, model: str = "", key_ref: str = "") -> bool:
        with self._lock:
            c = self.get(provider, model=model, key_ref=key_ref)
            before = c.state
            ok = c.allow()
            # half-open transition is a state change worth persisting
            if c.state != before:
                self._save_unlocked()
            return ok

    def success(self, provider: str, *, model: str = "", key_ref: str = "") -> None:
        with self._lock:
            self.get(provider, model=model, key_ref=key_ref).record_success()
            self._save_unlocked()

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
            self._save_unlocked()

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [c.as_dict() for c in self._circuits.values()]


_CIRCUITS: CircuitRegistry | None = None


def get_circuits() -> CircuitRegistry:
    global _CIRCUITS
    if _CIRCUITS is None:
        _CIRCUITS = CircuitRegistry(persist=True)
    return _CIRCUITS


def reset_circuits_for_tests() -> None:
    """Test helper: drop process-global registry."""
    global _CIRCUITS
    _CIRCUITS = None
