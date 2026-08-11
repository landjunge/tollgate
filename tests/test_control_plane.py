"""Control plane: health scores, consumer burn, explain, /v1/control."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_provider_health_and_consumer_burn(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config
    from tollgate.control_plane import consumer_burn, control_snapshot, provider_health
    from tollgate.usage_ledger import record_usage

    cfg = load_config(force=True)
    cfg["consumer_envelopes"] = {
        "support": {"max_usd_day": 1.0, "max_calls_day": 100},
    }
    save_config(cfg)

    record_usage(
        "deepseek",
        op="chat",
        tokens_in=100,
        tokens_out=50,
        usd=0.4,
        consumer="support",
        latency_ms=800,
    )
    record_usage(
        "deepseek",
        op="chat",
        tokens_in=10,
        tokens_out=5,
        usd=0.05,
        error=True,
        consumer="support",
        latency_ms=2000,
    )
    record_usage(
        "opencode_zen",
        op="chat",
        tokens_in=20,
        tokens_out=10,
        usd=0.0,
        consumer="coding",
        latency_ms=400,
    )

    health = {r["provider"]: r for r in provider_health()}
    assert health["deepseek"]["calls"] == 2
    assert health["deepseek"]["errors"] == 1
    assert health["deepseek"]["success_rate"] == 0.5
    assert health["deepseek"]["latency_ms_avg"] is not None
    assert health["opencode_zen"]["success_rate"] == 1.0

    burn = {r["consumer"]: r for r in consumer_burn()}
    assert burn["support"]["usd"] > 0
    assert burn["support"]["max_usd_day"] == 1.0
    assert burn["support"]["projected_usd_eod"] >= burn["support"]["usd"]
    assert "status" in burn["support"]

    snap = control_snapshot()
    assert snap["ok"] is True
    assert "headline" in snap
    assert snap["pillars"] == ["reliability", "cost", "control"]
    assert len(snap["providers"]) >= 2
    assert len(snap["consumers"]) >= 1


def test_explain_route_shape(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.control_plane import explain_route

    fake = {
        "ok": True,
        "provider": "opencode_zen",
        "model": "deepseek-v4-flash-free",
        "prefer_free": True,
        "route": {"provider": "opencode_zen", "model": "deepseek-v4-flash-free"},
        "fallbacks": [{"provider": "nvidia", "model": ""}],
        "tried": [{"provider": "openrouter", "skip": "not ready"}],
    }
    ex = explain_route(fake)
    assert ex["ok"] is True
    assert ex["selected"]["provider"] == "opencode_zen"
    assert isinstance(ex["reasons"], list) and len(ex["reasons"]) >= 1
    assert isinstance(ex["checks"], list)


def test_control_http_and_dashboard(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c

    c.clear_cache()
    from tollgate.server_v1 import app

    client = TestClient(app)
    r = client.get("/v1/control", headers={"X-Consumer-Key": "desk"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "headline" in body
    assert "providers" in body

    d = client.get("/dashboard")
    assert d.status_code == 200
    assert "text/html" in d.headers.get("content-type", "")
    assert "Control Plane" in d.text

    route = client.post(
        "/v1/route?explain=true",
        headers={"X-Consumer-Key": "desk"},
        json={"intent": "free_llm", "tokens_est": 100},
    )
    assert route.status_code == 200
    assert "explain" in route.json()
