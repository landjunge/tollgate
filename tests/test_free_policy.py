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


def test_free_llm_scope_no_route_when_only_paid_ready(monkeypatch, tmp_path):
    """
    Unnegotiable: allowed_intents=[free_llm], only paid providers ready → NO ROUTE.
    Paid names here stand in for OpenAI/Anthropic (deepseek/google).
    """
    from unittest.mock import MagicMock, patch

    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config
    from tollgate.chat_route import routed_chat
    from tollgate.limits import check_consumer_scope
    from tollgate.router import route

    cfg = load_config(force=True)
    cfg["prefer_free"] = True
    cfg["routing"] = dict(cfg.get("routing") or {})
    cfg["routing"]["intents"] = {
        "free_llm": ["opencode_zen", "deepseek", "google"],
        "llm": ["opencode_zen", "deepseek"],
    }
    cfg["consumer_envelopes"] = {
        "desk": {
            "allowed_intents": ["free_llm"],
            "allowed_providers": ["opencode_zen", "deepseek", "google"],
            "max_usd_day": 2,
        }
    }
    save_config(cfg)

    assert check_consumer_scope("desk", intent="free_llm")["allowed"] is True
    assert check_consumer_scope("desk", intent="llm")["allowed"] is False

    svc = MagicMock()
    svc.inventory.return_value = {
        "providers": [
            {"id": "opencode_zen", "ready": False, "grade": "F", "error": "down"},
            {"id": "deepseek", "ready": True, "grade": "A"},
            {"id": "google", "ready": True, "grade": "A"},
        ]
    }
    with patch("tollgate.router.admit") as ad:
        ad.return_value = MagicMock(
            allowed=True,
            soft_degrade=False,
            limits={},
            as_dict=lambda: {"allowed": True},
        )
        r = route(svc, "free_llm", prefer_free=True)

    assert r.get("ok") is False
    assert r.get("route") is None
    assert r.get("free_only") is True
    winner = (r.get("route") or {}).get("provider")
    assert winner not in ("deepseek", "google")

    out = routed_chat("hi", intent="llm", consumer="desk", provider="deepseek")
    assert out.get("ok") is False
    assert out.get("protection") == "scope"


def test_soft_fail_counts():
    from tollgate.soft_fail import reset_soft_fail_counts, soft_fail, soft_fail_counts

    reset_soft_fail_counts()
    soft_fail("audit", RuntimeError("boom"), message="test")
    assert soft_fail_counts().get("audit", 0) >= 1
    reset_soft_fail_counts()
