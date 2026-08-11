"""L3 consumer scopes — allow/block providers, ops, intents."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tollgate.gateway.admit import admit
from tollgate.gateway.context import RequestContext
from tollgate.limits import check_consumer_scope, check_limits


def test_allowed_providers_deny(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["consumer_envelopes"] = {
        "n8n": {
            "allowed_providers": ["opencode_zen", "brave"],
            "max_usd_day": 5,
        }
    }
    save_config(cfg)

    ok = check_consumer_scope("n8n", provider="opencode_zen")
    assert ok["allowed"] is True
    bad = check_consumer_scope("n8n", provider="deepseek")
    assert bad["allowed"] is False
    assert bad.get("protection") == "scope"
    assert "allowed_providers" in (bad.get("reason") or "")

    lim = check_limits("deepseek", op="chat", consumer="n8n")
    assert lim["allowed"] is False
    assert lim.get("protection") == "scope"

    d = admit(
        "deepseek",
        op="chat",
        tokens_est=10,
        ctx=RequestContext(consumer="n8n", agent_id="n8n"),
    )
    assert d.allowed is False
    assert "scope" in (d.reason or "").lower() or "allowed_providers" in (d.reason or "")


def test_blocked_providers(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["consumer_envelopes"] = {
        "agent": {"blocked_providers": ["google", "minimax"]},
    }
    save_config(cfg)
    assert check_consumer_scope("agent", provider="deepseek")["allowed"] is True
    bad = check_consumer_scope("agent", provider="google")
    assert bad["allowed"] is False
    assert "blocked_providers" in (bad.get("reason") or "")


def test_allowed_intents_and_ops(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["consumer_envelopes"] = {
        "search-bot": {
            "allowed_intents": ["search"],
            "allowed_ops": ["search", "status"],
            "allowed_providers": ["brave"],
        }
    }
    save_config(cfg)
    assert check_consumer_scope("search-bot", intent="search")["allowed"] is True
    assert check_consumer_scope("search-bot", intent="llm")["allowed"] is False
    assert check_consumer_scope("search-bot", op="search")["allowed"] is True
    assert check_consumer_scope("search-bot", op="chat")["allowed"] is False


def test_route_http_scope(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c
    from tollgate.app_config import load_config, save_config

    c.clear_cache()
    cfg = load_config(force=True)
    cfg["consumer_envelopes"] = {
        "n8n": {"allowed_intents": ["search", "free_llm"]},
    }
    save_config(cfg)

    from tollgate.server_v1 import app

    client = TestClient(app)
    r = client.post(
        "/v1/route",
        json={"intent": "tts"},
        headers={"X-Consumer-Key": "n8n"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is False
    assert body.get("protection") == "scope"


def test_cli_scope_flags(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.cli import main
    from tollgate.limits import check_consumer_scope, consumer_envelope

    main(
        [
            "consumer-budget",
            "lane",
            "--max-usd-day",
            "1",
            "--allow-provider",
            "brave",
            "--allow-provider",
            "opencode_zen",
            "--block-provider",
            "google",
            "--allow-intent",
            "search",
            "--allow-intent",
            "free_llm",
        ]
    )
    out = capsys.readouterr().out
    assert '"ok": true' in out or '"ok": true' in out.lower() or '"ok": true' in out
    env = consumer_envelope("lane")
    assert "brave" in env["allowed_providers"]
    assert "google" in env["blocked_providers"]
    assert check_consumer_scope("lane", provider="deepseek")["allowed"] is False
