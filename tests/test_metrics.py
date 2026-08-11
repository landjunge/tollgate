"""Prometheus /metrics exposition."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_metrics_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
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


def test_render_prometheus_smoke(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.metrics import render_prometheus

    out = render_prometheus()
    assert out.startswith("# HELP")
    assert "tollgate_up 1" in out
