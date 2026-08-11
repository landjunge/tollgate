"""Product REQUEST BLOCKED card on agent-protection denies."""

from __future__ import annotations

from tollgate.block_view import build_block_card
from tollgate.gateway.entry import gateway_call
from tollgate.gateway.context import RequestContext


def test_build_block_card_tool_calls():
    card = build_block_card(
        reason="agent protection: consumer support-agent max_tool_calls 99 > 20",
        consumer="support-agent",
        provider="opencode_zen",
        op="chat",
        protection="max_tool_calls",
        limits={
            "protection": "max_tool_calls",
            "envelope": {"max_tool_calls": 20, "max_usd_request": 0.5},
        },
        tool_calls_est=99,
    )
    assert card["headline"] == "REQUEST BLOCKED"
    assert card["consumer"] == "support-agent"
    assert card["reason"] == "max_tool_calls"
    assert card["tool_calls"]["est"] == 99
    assert card["tool_calls"]["max"] == 20
    assert "REQUEST BLOCKED" in card["message"]
    assert "99" in card["message"]


def test_gateway_deny_includes_blocked(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["consumer_envelopes"] = {
        "support-agent": {"max_tool_calls": 3, "max_usd_day": 5},
    }
    save_config(cfg)

    ctx = RequestContext(consumer="support-agent", tool_calls_est=99, agent_id="support-agent")
    out = gateway_call("opencode_zen", "chat", ctx=ctx, tokens_est=10, message="x")
    assert out.get("ok") is False
    assert out.get("blocked")
    assert out["blocked"]["headline"] == "REQUEST BLOCKED"
    assert out["blocked"]["protection"] == "max_tool_calls"
    assert "message" in out
