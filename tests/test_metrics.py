"""Prometheus /metrics exposition + auth policy."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient


def test_metrics_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    monkeypatch.delenv("TOLLGATE_METRICS_TOKEN", raising=False)
    monkeypatch.delenv("TOLLGATE_METRICS_PUBLIC", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c
    from tollgate.usage_ledger import record_usage

    c.clear_cache()
    record_usage("deepseek", op="chat", tokens_in=10, tokens_out=5, usd=0.01, root=tmp_path)

    from tollgate.server_v1 import app

    client = TestClient(app)
    r = client.get("/metrics")
    assert r.status_code == 200
    text = r.text
    assert "tollgate_up 1" in text
    assert "tollgate_usage_calls_total" in text
    assert "tollgate_provider_calls_total" in text
    assert 'provider="deepseek"' in text


def test_metrics_token_required(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.setenv("TOLLGATE_METRICS_TOKEN", "scrape-secret-xyz")
    monkeypatch.delenv("TOLLGATE_METRICS_PUBLIC", raising=False)
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c

    c.clear_cache()
    from tollgate.server_v1 import app

    client = TestClient(app)
    assert client.get("/metrics").status_code == 401
    ok = client.get("/metrics", headers={"X-Metrics-Token": "scrape-secret-xyz"})
    assert ok.status_code == 200
    assert "tollgate_up 1" in ok.text
    ok2 = client.get("/metrics", headers={"Authorization": "Bearer scrape-secret-xyz"})
    assert ok2.status_code == 200


def test_metrics_auth_mode_requires_consumer(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_METRICS_TOKEN", raising=False)
    monkeypatch.delenv("TOLLGATE_METRICS_PUBLIC", raising=False)
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    ud = tmp_path / "User"
    ud.mkdir(parents=True)
    from tollgate import consumers as c
    from tollgate.consumers import add_consumer

    c.clear_cache()
    out = add_consumer("desk", secret="desksecret99", admin=True)
    assert out.get("ok")
    c.clear_cache()

    from tollgate.server_v1 import app

    client = TestClient(app)
    assert client.get("/metrics").status_code == 401
    r = client.get(
        "/metrics",
        headers={"X-Consumer-Key": "desk:desksecret99"},
    )
    assert r.status_code == 200
    assert "tollgate_up 1" in r.text


def test_metrics_public_override(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.setenv("TOLLGATE_REQUIRE_AUTH", "1")
    monkeypatch.setenv("TOLLGATE_METRICS_PUBLIC", "1")
    monkeypatch.delenv("TOLLGATE_METRICS_TOKEN", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    # empty consumers but REQUIRE_AUTH
    (tmp_path / "User" / "consumers.json").write_text(
        json.dumps({"version": 1, "consumers": []}), encoding="utf-8"
    )
    from tollgate import consumers as c

    c.clear_cache()
    from tollgate.server_v1 import app

    client = TestClient(app)
    assert client.get("/metrics").status_code == 200


def test_render_prometheus_smoke(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.metrics import render_prometheus

    out = render_prometheus()
    assert out.startswith("# HELP")
    assert "tollgate_up 1" in out
