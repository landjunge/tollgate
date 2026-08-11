"""Configurable circuit jitter + defaults from keys_app."""

from __future__ import annotations

import time

from tollgate.gateway.circuit import (
    Circuit,
    CircuitRegistry,
    CircuitState,
    _circuit_defaults,
    reset_circuits_for_tests,
)


def test_jitter_factor_respects_range():
    c = Circuit(provider="x", jitter_min=0.9, jitter_max=1.1)
    factors = [c._jitter_factor() for _ in range(200)]
    assert all(0.9 <= f <= 1.1 for f in factors)
    # Should actually spread (not stuck at one edge)
    assert max(factors) - min(factors) > 0.05


def test_jitter_factor_swaps_inverted_range():
    c = Circuit(provider="x", jitter_min=1.2, jitter_max=0.8)
    factors = [c._jitter_factor() for _ in range(50)]
    assert all(0.8 <= f <= 1.2 for f in factors)


def test_jitter_factor_equal_bounds():
    c = Circuit(provider="x", jitter_min=1.0, jitter_max=1.0)
    assert c._jitter_factor() == 1.0


def test_allow_open_uses_jittered_wait(monkeypatch):
    c = Circuit(
        provider="brave",
        state=CircuitState.OPEN,
        opened_at=time.time() - 10.0,
        cooldown_s=30.0,
        jitter_min=0.5,
        jitter_max=0.5,  # fixed 50% → wait = 15s; 10s elapsed → still closed
    )
    assert c.allow() is False
    assert c.state == CircuitState.OPEN

    c2 = Circuit(
        provider="brave",
        state=CircuitState.OPEN,
        opened_at=time.time() - 20.0,
        cooldown_s=30.0,
        jitter_min=0.5,
        jitter_max=0.5,  # wait = 15s; 20s elapsed → half_open
    )
    assert c2.allow() is True
    assert c2.state == CircuitState.HALF_OPEN


def test_hard_failure_uses_hard_cooldown():
    c = Circuit(
        provider="deepseek",
        cooldown_s=30.0,
        hard_cooldown_s=120.0,
        failure_threshold=99,
    )
    c.record_failure(message="401", hard=True)
    assert c.state == CircuitState.OPEN
    assert c.cooldown_s >= 120.0


def test_hard_cooldown_stays_elevated_after_soft_recovery():
    """Documented behavior: hard open elevates cooldown_s and keeps it after CLOSE."""
    c = Circuit(
        provider="deepseek",
        cooldown_s=30.0,
        hard_cooldown_s=120.0,
        failure_threshold=99,
        half_open_successes_needed=1,
    )
    c.record_failure(message="401", hard=True)
    assert c.cooldown_s >= 120.0
    c.state = CircuitState.HALF_OPEN
    c.record_success()
    assert c.state == CircuitState.CLOSED
    # sticky elevated soft cooldown (not reset) — AUTH_DEAD stays cold
    assert c.cooldown_s >= 120.0


def test_registry_applies_config_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    # Write a custom circuits block
    cfg_path = tmp_path / "User" / "keys_app.json"
    cfg_path.write_text(
        """{
      "version": 2,
      "circuits": {
        "jitter_min": 0.5,
        "jitter_max": 0.6,
        "cooldown_s": 12.0,
        "failure_threshold": 3,
        "hard_cooldown_s": 90.0
      }
    }
    """,
        encoding="utf-8",
    )
    reset_circuits_for_tests()
    # Force config reload from our temp home
    from tollgate import app_config

    app_config._CACHE = None
    app_config._CACHE_MTIME = None

    r = CircuitRegistry(root=tmp_path, persist=False)
    c = r.get("openrouter", model="free")
    assert c.jitter_min == 0.5
    assert c.jitter_max == 0.6
    assert c.cooldown_s == 12.0
    assert c.failure_threshold == 3
    assert c.hard_cooldown_s == 90.0

    reset_circuits_for_tests()
    app_config._CACHE = None
    app_config._CACHE_MTIME = None


def test_circuit_defaults_helper_clamps():
    d = _circuit_defaults()
    assert d["jitter_min"] > 0
    assert d["jitter_max"] >= d["jitter_min"]
