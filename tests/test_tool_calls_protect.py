"""HTTP invoke tool_calls_est + MCP protect check."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_invoke_tool_calls_est_blocked(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c
    from tollgate.app_config import load_config, save_config

    c.clear_cache()
    cfg = load_config(force=True)
    cfg["consumer_envelopes"] = {"agent": {"max_tool_calls": 3}}
    provs = dict(cfg.get("providers") or {})
    provs["deepseek"] = dict(provs.get("deepseek") or {}, enabled=True)
    cfg["providers"] = provs
    save_config(cfg)

    from tollgate.server_v1 import app

    client = TestClient(app)
    r = client.post(
        "/v1/invoke",
        headers={"X-Consumer-Key": "agent"},
        json={
            "provider": "deepseek",
            "op": "chat",
            "tool_calls_est": 12,
            "tokens_est": 100,
            "arguments": {"message": "hi", "max_tokens": 8},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is False
    assert "max_tool_calls" in (body.get("error") or "")


def test_invoke_infers_tool_calls_from_arguments_list(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c
    from tollgate.app_config import load_config, save_config

    c.clear_cache()
    cfg = load_config(force=True)
    cfg["consumer_envelopes"] = {"agent": {"max_tool_calls": 2}}
    save_config(cfg)

    from tollgate.server_v1 import app

    client = TestClient(app)
    r = client.post(
        "/v1/invoke",
        headers={"X-Consumer-Key": "agent"},
        json={
            "provider": "deepseek",
            "op": "chat",
            "arguments": {
                "message": "hi",
                "tools": [{"name": "a"}, {"name": "b"}, {"name": "c"}],
            },
        },
    )
    body = r.json()
    assert body.get("ok") is False
    assert "max_tool_calls" in (body.get("error") or "")


def test_mcp_agent_protect_check_registered():
    from tollgate.mcp_tools import KEYS_MCP_TOOLS

    names = {t["name"] for t in KEYS_MCP_TOOLS}
    assert "keys_control" in names
    assert "keys_resilience" in names
    assert "keys_chaos_status" in names
    assert "keys_agent_protect_check" in names
    # dry-run handler
    tool = next(t for t in KEYS_MCP_TOOLS if t["name"] == "keys_agent_protect_check")
    out = tool["handler"](consumer="x", tokens_est=10, tool_calls_est=0)
    assert "allowed" in out
