"""Per-consumer day budget envelopes + ledger attribution."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_ledger_tracks_consumer(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.usage_ledger import consumer_usage, load_usage, record_usage

    record_usage("deepseek", op="chat", tokens_in=10, tokens_out=5, consumer="n8n")
    record_usage("deepseek", op="chat", tokens_in=20, tokens_out=5, consumer="gnom")
    record_usage("brave", op="search", tokens_in=0, tokens_out=0, consumer="n8n")

    n8n = consumer_usage("n8n")
    assert n8n["calls"] == 2
    assert n8n["tokens"] == 15
    gnom = consumer_usage("gnom")
    assert gnom["calls"] == 1
    assert gnom["tokens"] == 25

    day = load_usage()
    assert "n8n" in (day.get("consumers") or {})
    assert "gnom" in (day.get("consumers") or {})
    assert int((day.get("providers") or {}).get("deepseek", {}).get("calls") or 0) == 2


def test_consumer_envelope_deny(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config
    from tollgate.gateway.admit import admit
    from tollgate.gateway.context import RequestContext
    from tollgate.usage_ledger import record_usage

    cfg = load_config(force=True)
    cfg["consumer_envelopes"] = {
        "n8n": {"max_calls_day": 2, "max_tokens_day": 0, "max_usd_day": 0},
    }
    save_config(cfg)

    record_usage("deepseek", op="chat", tokens_in=1, tokens_out=1, consumer="n8n")
    record_usage("deepseek", op="chat", tokens_in=1, tokens_out=1, consumer="n8n")

    # gnom still allowed (no envelope)
    ok = admit(
        "deepseek",
        op="chat",
        tokens_est=10,
        ctx=RequestContext(consumer="gnom", agent_id="gnom"),
    )
    assert ok.allowed is True

    denied = admit(
        "deepseek",
        op="chat",
        tokens_est=10,
        ctx=RequestContext(consumer="n8n", agent_id="n8n"),
    )
    assert denied.allowed is False
    assert "n8n" in (denied.reason or "")
    assert "max_calls_day" in (denied.reason or "")


def test_consumer_usd_envelope(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config
    from tollgate.limits import check_consumer_limits
    from tollgate.usage_ledger import record_usage

    cfg = load_config(force=True)
    cfg["consumer_envelopes"] = {
        "batch": {"max_usd_day": 0.000001},  # tiny — any real spend denies next
    }
    save_config(cfg)
    # force usd via explicit param
    record_usage(
        "deepseek",
        op="chat",
        tokens_in=0,
        tokens_out=0,
        usd=0.01,
        consumer="batch",
    )
    lim = check_consumer_limits("batch")
    assert lim["allowed"] is False
    assert "max_usd_day" in (lim.get("reason") or "")


def test_budget_endpoint_includes_envelope(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c
    from tollgate.app_config import load_config, save_config

    c.clear_cache()
    cfg = load_config(force=True)
    cfg["consumer_envelopes"] = {
        "n8n": {"max_calls_day": 50, "max_usd_day": 1.0},
    }
    save_config(cfg)

    from tollgate.server_v1 import app

    client = TestClient(app)
    r = client.get("/v1/budget", headers={"X-Consumer-Key": "n8n"})
    assert r.status_code == 200
    body = r.json()
    assert body["consumer"] == "n8n"
    assert body["consumer_envelope"]["max_calls_day"] == 50
    assert body["consumer_limits"]["allowed"] is True
    assert "consumer_usage" in body
