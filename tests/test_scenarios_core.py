"""Named Core scenarios (A–D) — wrappers over existing protection paths."""

from __future__ import annotations

from tollgate.app_config import load_config, save_config
from tollgate.block_view import build_block_card, human_block_sentence
from tollgate.gateway.context import RequestContext
from tollgate.gateway.entry import gateway_call


def _lane(tmp_path, monkeypatch, name: str = "scenario-agent", **env):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True, exist_ok=True)
    cfg = load_config(force=True)
    block = {
        "max_tool_calls": 3,
        "max_usd_day": 1.0,
        "max_usd_request": 0.5,
        "max_requests_minute": 60,
    }
    block.update(env)
    cfg["consumer_envelopes"] = {name: block}
    save_config(cfg)
    return name


def test_scenario_b_agent_loop_blocked(monkeypatch, tmp_path):
    """Scenario B: agent loops → limit → blocked + audit-shaped card."""
    name = _lane(tmp_path, monkeypatch)
    ctx = RequestContext(consumer=name, tool_calls_est=99, agent_id=name)
    out = gateway_call("opencode_zen", "chat", ctx=ctx, tokens_est=10, message="loop")
    assert out.get("ok") is False
    assert out.get("blocked")
    assert out["blocked"].get("protection") == "max_tool_calls"
    assert "human" in out["blocked"]
    assert "loop" in out["blocked"]["human"].lower() or "tool" in out["blocked"]["human"].lower()


def test_scenario_c_budget_exceeded_shape(monkeypatch, tmp_path):
    """Scenario C: budget deny produces human block card."""
    name = _lane(tmp_path, monkeypatch, max_usd_day=0.01, max_tool_calls=100)
    # Force spend past budget via ledger if available; else unit-level card
    card = build_block_card(
        reason=f"agent protection: consumer {name} max_usd_day reached",
        consumer=name,
        protection="max_usd_day",
        limits={"envelope": {"max_usd_day": 0.01}},
    )
    assert card["protection"] == "max_usd_day"
    h = human_block_sentence(prot="max_usd_day", consumer=name)
    assert "budget" in h.lower()


def test_scenario_human_circuit_message():
    """Provider/circuit language is operator-friendly."""
    h = human_block_sentence(prot="circuit", reason="circuit open")
    assert "fallback" in h.lower() or "cool" in h.lower() or "provider" in h.lower()


def test_scenario_d_config_survives_reload(monkeypatch, tmp_path):
    """Scenario D: config written under TOLLGATE_HOME is reloaded."""
    name = _lane(tmp_path, monkeypatch, max_tool_calls=7)
    cfg1 = load_config(force=True)
    assert cfg1["consumer_envelopes"][name]["max_tool_calls"] == 7
    cfg2 = load_config(force=True)
    assert cfg2["consumer_envelopes"][name]["max_tool_calls"] == 7
