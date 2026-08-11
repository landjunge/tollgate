"""Agent protection: request/hour/minute hard stops."""

from __future__ import annotations

from unittest.mock import patch

from tollgate.gateway.admit import admit
from tollgate.gateway.context import RequestContext
from tollgate.gateway.entry import gateway_call
from tollgate.limits import check_consumer_limits


def test_max_tokens_request(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["consumer_envelopes"] = {
        "loop": {"max_tokens_request": 100},
    }
    save_config(cfg)

    ok = check_consumer_limits("loop", tokens_est=50)
    assert ok["allowed"] is True
    bad = check_consumer_limits("loop", tokens_est=500)
    assert bad["allowed"] is False
    assert bad.get("protection") == "max_tokens_request"
    assert "agent protection" in (bad.get("reason") or "")


def test_max_usd_request(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["consumer_envelopes"] = {"loop": {"max_usd_request": 0.001}}
    save_config(cfg)
    # explicit usd_est over limit
    bad = check_consumer_limits("loop", tokens_est=1, usd_est=1.0)
    assert bad["allowed"] is False
    assert bad.get("protection") == "max_usd_request"


def test_max_requests_minute(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.agent_guard import record_attempt
    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["consumer_envelopes"] = {"loop": {"max_requests_minute": 2}}
    save_config(cfg)

    record_attempt("loop", tokens_est=10)
    record_attempt("loop", tokens_est=10)
    bad = check_consumer_limits("loop", tokens_est=10)
    assert bad["allowed"] is False
    assert bad.get("protection") == "max_requests_minute"


def test_max_tool_calls(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["consumer_envelopes"] = {"loop": {"max_tool_calls": 3}}
    save_config(cfg)
    assert check_consumer_limits("loop", tool_calls_est=2)["allowed"] is True
    bad = check_consumer_limits("loop", tool_calls_est=9)
    assert bad["allowed"] is False
    assert bad.get("protection") == "max_tool_calls"


def test_admit_blocks_and_gateway_counts(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["consumer_envelopes"] = {
        "agent": {"max_requests_minute": 1, "max_tokens_request": 50_000},
    }
    # keep deepseek enabled for admit path
    provs = dict(cfg.get("providers") or {})
    provs["deepseek"] = dict(provs.get("deepseek") or {}, enabled=True)
    cfg["providers"] = provs
    save_config(cfg)

    ctx = RequestContext(consumer="agent", agent_id="agent")
    d1 = admit("deepseek", op="chat", tokens_est=100, ctx=ctx)
    assert d1.allowed is True

    # first gateway_call records attempt after admit
    with patch("tollgate.get_keys_service") as gs:
        mock_svc = gs.return_value
        mock_svc.call.return_value = {
            "ok": True,
            "content": "hi",
            "provider": "deepseek",
        }
        out = gateway_call("deepseek", "chat", ctx=ctx, tokens_est=100, model="x")
    assert out.get("ok") is True

    # second admit should hit max_requests_minute
    d2 = admit("deepseek", op="chat", tokens_est=100, ctx=ctx)
    assert d2.allowed is False
    assert "max_requests_minute" in (d2.reason or "")
