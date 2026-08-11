"""Execute-time failover across route candidates."""

from __future__ import annotations

from unittest.mock import patch

import pytest


def test_is_retriable():
    from tollgate.failover import is_retriable_failure

    assert is_retriable_failure({"ok": False, "error_class": "PROVIDER_DOWN"}) is True
    assert is_retriable_failure({"ok": False, "error_class": "RATE_LIMIT"}) is True
    assert is_retriable_failure({"ok": False, "error_class": "BUDGET_HARD"}) is False
    assert is_retriable_failure({"ok": False, "error_class": "POLICY_DENY"}) is False
    assert is_retriable_failure({"ok": True, "content": "hi"}) is False


def test_routed_chat_fails_over(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)

    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["auto_failover"] = True
    save_config(cfg)

    calls: list[str] = []

    def fake_gateway(provider, op, **kwargs):
        calls.append(provider)
        if provider == "opencode_zen":
            return {
                "ok": False,
                "error": "upstream 503",
                "error_class": "PROVIDER_DOWN",
                "provider": provider,
            }
        return {
            "ok": True,
            "content": "from-deepseek",
            "provider": provider,
            "model": "deepseek-v4-flash",
            "prompt_tokens": 1,
            "completion_tokens": 1,
        }

    built = {
        "ok": True,
        "candidates": [
            {"provider": "opencode_zen", "model": "deepseek-v4-flash-free"},
            {"provider": "deepseek", "model": "deepseek-v4-flash"},
        ],
        "auto_failover": True,
        "pinned": False,
    }

    with patch("tollgate.chat_route.build_candidates", return_value=built), patch(
        "tollgate.chat_route.gateway_call", side_effect=fake_gateway
    ):
        from tollgate.chat_route import routed_chat

        out = routed_chat("hi", intent="free_llm", consumer="desk")

    assert out["ok"] is True
    assert out["content"] == "from-deepseek"
    assert out["provider"] == "deepseek"
    assert calls == ["opencode_zen", "deepseek"]
    assert out["failover"]["hops"] == 2
    assert out["failover"]["winner"] == "deepseek"


def test_routed_chat_no_failover_on_budget(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)

    calls: list[str] = []

    def fake_gateway(provider, op, **kwargs):
        calls.append(provider)
        return {
            "ok": False,
            "error": "max_usd_day reached",
            "error_class": "BUDGET_HARD",
        }

    built = {
        "ok": True,
        "candidates": [
            {"provider": "opencode_zen", "model": "x"},
            {"provider": "deepseek", "model": "y"},
        ],
        "auto_failover": True,
    }

    with patch("tollgate.chat_route.build_candidates", return_value=built), patch(
        "tollgate.chat_route.gateway_call", side_effect=fake_gateway
    ):
        from tollgate.chat_route import routed_chat

        out = routed_chat("hi", consumer="n8n")

    assert out["ok"] is False
    assert calls == ["opencode_zen"]  # no hop on budget
    assert out["failover"]["exhausted"] is True or out["failover"]["hops"] == 1


def test_pinned_provider_no_multi_hop(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)

    from tollgate.failover import build_candidates

    out = build_candidates(provider="deepseek", model="m", intent="llm")
    assert out["ok"] is True
    assert len(out["candidates"]) == 1
    assert out["candidates"][0]["provider"] == "deepseek"
    assert out.get("pinned") is True
