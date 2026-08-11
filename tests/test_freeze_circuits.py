"""Global freeze kill switch + circuit reset."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tollgate.gateway.admit import admit
from tollgate.gateway.context import RequestClass, RequestContext


def test_freeze_denies_billable(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_FROZEN", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.freeze import set_frozen, freeze_status
    from tollgate import app_config

    app_config._CACHE = None
    set_frozen(True, reason="test kill", by="pytest", root=tmp_path)
    assert freeze_status()["frozen"] is True

    d = admit(
        "deepseek",
        op="chat",
        tokens_est=10,
        ctx=RequestContext(consumer="n8n"),
    )
    assert d.allowed is False
    assert "frozen" in (d.reason or "").lower()
    assert (d.limits or {}).get("protection") == "freeze"

    # system may still pass
    d2 = admit(
        "deepseek",
        op="status",
        ctx=RequestContext.system(agent_id="probe"),
    )
    # may still fail for other reasons (no key) but not freeze
    if not d2.allowed:
        assert "frozen" not in (d2.reason or "").lower()

    set_frozen(False, by="pytest", root=tmp_path)
    assert freeze_status()["frozen"] is False


def test_env_freeze_override(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.setenv("TOLLGATE_FROZEN", "1")
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.freeze import freeze_status, is_frozen

    assert is_frozen() is True
    assert freeze_status()["source"] == "env"


def test_freeze_check_error_fail_closed(monkeypatch, tmp_path):
    """Kill switch must not silently pass if freeze module raises."""
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_FROZEN", raising=False)
    (tmp_path / "User").mkdir(parents=True)

    def _boom():
        raise RuntimeError("freeze module broken")

    monkeypatch.setattr("tollgate.freeze.is_frozen", _boom)
    d = admit(
        "deepseek",
        op="chat",
        tokens_est=10,
        ctx=RequestContext(consumer="n8n"),
    )
    assert d.allowed is False
    assert "fail-closed" in (d.reason or "").lower()
    assert (d.limits or {}).get("freeze_check_error") is True


def test_circuit_reset(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.gateway.circuit import (
        CircuitState,
        CircuitRegistry,
        get_circuits,
        reset_circuits,
        reset_circuits_for_tests,
    )

    reset_circuits_for_tests()
    reg = get_circuits()
    # use registry API so root/persist is consistent
    reg = CircuitRegistry(root=tmp_path, persist=True)
    c = reg.get("deepseek", model="flash")
    c.state = CircuitState.OPEN
    c.failures = 9
    with reg._lock:
        reg._save_unlocked()
    assert any(r.get("state") == "open" for r in reg.snapshot())

    out = reg.reset("deepseek")
    assert out["ok"]
    assert out["removed_n"] >= 1
    assert not any(
        r.get("provider") == "deepseek" and r.get("state") == "open"
        for r in reg.snapshot()
    )
    reset_circuits_for_tests()


def test_circuit_mtime_reload_across_registries(monkeypatch, tmp_path):
    """Worker B must see Worker A's OPEN after circuits.json mtime changes."""
    import time

    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.gateway.circuit import CircuitRegistry, CircuitState

    a = CircuitRegistry(root=tmp_path, persist=True)
    c = a.get("brave", model="*")
    c.state = CircuitState.OPEN
    c.opened_at = time.time()  # still in cooldown
    c.cooldown_s = 300.0
    c.jitter_min = 1.0
    c.jitter_max = 1.0
    with a._lock:
        a._save_unlocked()

    b = CircuitRegistry(root=tmp_path, persist=True)
    # Stale empty memory — must re-read disk on access
    b._circuits = {}
    b._mtime = None
    assert b.allow("brave", model="*") is False
    snap = b.snapshot()
    assert any(
        r.get("provider") == "brave" and r.get("state") == "open" for r in snap
    )


def test_freeze_http(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    monkeypatch.delenv("TOLLGATE_FROZEN", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c
    from tollgate import app_config

    c.clear_cache()
    app_config._CACHE = None

    from tollgate.server_v1 import app

    client = TestClient(app)
    r = client.get("/v1/freeze", headers={"X-Consumer-Key": "desk"})
    assert r.status_code == 200
    assert r.json()["frozen"] is False

    r2 = client.post(
        "/v1/freeze",
        json={"frozen": True, "reason": "http test"},
        headers={"X-Consumer-Key": "desk"},
    )
    assert r2.status_code == 200
    assert r2.json()["frozen"] is True

    h = client.get("/v1/health")
    assert h.json().get("freeze", {}).get("frozen") is True
    # health ok false when frozen
    assert h.json().get("ok") is False

    client.post(
        "/v1/freeze",
        json={"frozen": False},
        headers={"X-Consumer-Key": "desk"},
    )


def test_cli_freeze(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_FROZEN", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.cli import main
    from tollgate.freeze import is_frozen

    try:
        main(["freeze", "on", "--reason", "cli-test"])
    except SystemExit as e:
        assert e.code in (0, None)
    assert is_frozen() is True
    main(["freeze", "status"])
    out = capsys.readouterr().out
    assert "frozen" in out
    try:
        main(["freeze", "off"])
    except SystemExit:
        pass
    assert is_frozen() is False
