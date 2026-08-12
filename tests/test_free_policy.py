"""M10 FreePolicy — single free/paid truth."""

from __future__ import annotations


def test_free_llm_no_spend_no_spillover():
    from tollgate.protect.free_policy import resolve

    p = resolve(intent="free_llm", prefer_free=True, config={"prefer_free": True})
    assert p.free_only is True
    assert p.may_spend is False
    assert p.prefer_free is True
    chain, skips = p.order_chain(["opencode_zen", "deepseek", "google"])
    assert "deepseek" not in chain
    assert "opencode_zen" in chain
    assert any(s.get("provider") == "deepseek" for s in skips)


def test_llm_prefer_free_may_spend():
    from tollgate.protect.free_policy import resolve
    from tollgate.gateway.context import RequestClass

    p = resolve(intent="llm", prefer_free=True, config={"prefer_free": True})
    assert p.free_only is False
    assert p.may_spend is True
    assert p.request_class == RequestClass.FREE
    chain, _ = p.order_chain(["deepseek", "opencode_zen"])
    # free first
    assert chain[0] == "opencode_zen"
    assert "deepseek" in chain


def test_admit_free_gate_high_risk(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.gateway.context import RequestClass, RequestContext
    from tollgate.protect.free_policy import admit_free_gate

    ctx = RequestContext(request_class=RequestClass.FREE, allow_paid_fallback=False)
    # deepseek is typically high_risk via distill/config — mock
    from unittest.mock import patch

    with patch("tollgate.cost.is_high_risk", return_value=True):
        reason = admit_free_gate("deepseek", ctx)
    assert reason and "high-risk" in reason


def test_soft_fail_counts():
    from tollgate.soft_fail import reset_soft_fail_counts, soft_fail, soft_fail_counts

    reset_soft_fail_counts()
    soft_fail("audit", RuntimeError("boom"), message="test")
    assert soft_fail_counts().get("audit", 0) >= 1
    reset_soft_fail_counts()
