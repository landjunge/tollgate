"""Health-aware route ranking."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from tollgate.router import _rank_winners, route


def test_rank_prefers_higher_health_score():
    winners = [
        {"provider": "deepseek", "model": "a", "priority": 50},
        {"provider": "opencode_zen", "model": "b", "priority": 50},
    ]
    health = {
        "deepseek": {
            "provider": "deepseek",
            "score": 40.0,
            "status": "degraded",
            "success_rate": 0.4,
            "latency_ms_avg": 8000,
            "usd": 1.0,
            "circuit": "closed",
        },
        "opencode_zen": {
            "provider": "opencode_zen",
            "score": 98.0,
            "status": "healthy",
            "success_rate": 0.99,
            "latency_ms_avg": 400,
            "usd": 0.0,
            "circuit": "closed",
        },
    }
    with patch("tollgate.router._health_map", return_value=health):
        ranked = _rank_winners(
            winners,
            chain=["deepseek", "opencode_zen"],
            strategy="balanced",
            health_aware=True,
        )
    assert ranked[0]["provider"] == "opencode_zen"
    assert ranked[0]["rank_score"] > ranked[1]["rank_score"]
    assert ranked[0].get("rank_reasons")


def test_cost_strategy_prefers_cheaper_when_health_similar():
    winners = [
        {"provider": "deepseek", "model": "a", "priority": 50},
        {"provider": "openrouter", "model": "b", "priority": 50},
    ]
    health = {
        "deepseek": {
            "score": 90.0,
            "status": "healthy",
            "success_rate": 0.95,
            "latency_ms_avg": 1000,
            "usd": 5.0,
            "circuit": "closed",
        },
        "openrouter": {
            "score": 90.0,
            "status": "healthy",
            "success_rate": 0.95,
            "latency_ms_avg": 1000,
            "usd": 0.01,
            "circuit": "closed",
        },
    }
    with patch("tollgate.router._health_map", return_value=health):
        ranked = _rank_winners(
            winners,
            chain=["deepseek", "openrouter"],
            strategy="cost_optimized",
            health_aware=True,
        )
    assert ranked[0]["provider"] == "openrouter"


def test_health_aware_false_keeps_collect_order():
    winners = [
        {"provider": "deepseek", "model": "a", "priority": 50},
        {"provider": "opencode_zen", "model": "b", "priority": 50},
    ]
    out = _rank_winners(
        winners,
        chain=["deepseek", "opencode_zen"],
        strategy="balanced",
        health_aware=False,
    )
    assert out[0]["provider"] == "deepseek"


def test_route_includes_ranking(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["routing"] = dict(cfg.get("routing") or {})
    cfg["routing"]["health_aware"] = True
    cfg["routing"]["strategy"] = "balanced"
    cfg["routing"]["intents"] = {
        "free_llm": ["deepseek", "opencode_zen"],
    }
    save_config(cfg)

    svc = MagicMock()
    svc.inventory.return_value = {
        "providers": [
            {"id": "deepseek", "ready": True, "grade": "B"},
            {"id": "opencode_zen", "ready": True, "grade": "A"},
        ]
    }

    healthy = {
        "deepseek": {
            "score": 30.0,
            "status": "degraded",
            "success_rate": 0.3,
            "latency_ms_avg": 9000,
            "usd": 2.0,
            "circuit": "closed",
        },
        "opencode_zen": {
            "score": 99.0,
            "status": "healthy",
            "success_rate": 1.0,
            "latency_ms_avg": 300,
            "usd": 0.0,
            "circuit": "closed",
        },
    }

    with patch("tollgate.router.admit") as ad, patch(
        "tollgate.router._health_map", return_value=healthy
    ):
        ad.return_value = MagicMock(
            allowed=True,
            soft_degrade=False,
            limits={},
            as_dict=lambda: {"allowed": True},
        )
        r = route(svc, "free_llm", prefer_free=True)

    assert r["ok"] is True
    assert r["health_aware"] is True
    assert r["strategy"] == "balanced"
    assert r["route"]["provider"] == "opencode_zen"
    assert isinstance(r.get("ranking"), list) and len(r["ranking"]) >= 1
