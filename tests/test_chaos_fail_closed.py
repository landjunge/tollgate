"""Chaos / protection subsystem errors must fail-closed, never silent pass."""

from __future__ import annotations

from unittest.mock import patch

from tollgate.gateway.context import RequestContext
from tollgate.gateway.entry import gateway_call


def test_gateway_chaos_check_exception_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)

    with patch(
        "tollgate.chaos.is_provider_unavailable",
        side_effect=RuntimeError("chaos state unreadable"),
    ):
        out = gateway_call(
            "deepseek",
            "status",
            ctx=RequestContext(consumer="desk", agent_id="desk"),
        )

    assert out.get("ok") is False
    assert out.get("protection_error") is True
    assert "fail-closed" in (out.get("error") or "").lower()
