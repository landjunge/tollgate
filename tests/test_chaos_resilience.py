"""Chaos inject + failover test + resilience score."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from tollgate.chaos import is_provider_in_chaos, run_failover_test, start_chaos, stop_chaos
from tollgate.resilience import resilience_score
from tollgate.router import route


def test_chaos_inject_skips_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)

    start_chaos("opencode_zen", duration_s=60)
    assert is_provider_in_chaos("opencode_zen") is True

    svc = MagicMock()
    svc.inventory.return_value = {
        "providers": [
            {"id": "opencode_zen", "ready": True, "grade": "A"},
            {"id": "deepseek", "ready": True, "grade": "B"},
        ]
    }
    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["routing"] = dict(cfg.get("routing") or {})
    cfg["routing"]["health_aware"] = False
    # use llm intent so deepseek stays in chain even if not free_llm-capable
    cfg["routing"]["intents"] = {"llm": ["opencode_zen", "deepseek"]}
    provs = dict(cfg.get("providers") or {})
    for pid in ("opencode_zen", "deepseek"):
        provs[pid] = dict(provs.get(pid) or {}, enabled=True)
    cfg["providers"] = provs
    save_config(cfg)

    with patch("tollgate.router.admit") as ad:
        ad.return_value = MagicMock(
            allowed=True,
            soft_degrade=False,
            limits={},
            as_dict=lambda: {"allowed": True},
        )
        r = route(svc, "llm", prefer_free=False)

    assert r["ok"] is True, r
    assert r["route"]["provider"] == "deepseek"
    assert any(
        t.get("chaos") and t.get("provider") == "opencode_zen" for t in r.get("tried") or []
    )
    stop_chaos("opencode_zen")
    assert is_provider_in_chaos("opencode_zen") is False


def test_failover_test_report(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)

    # route always succeeds on deepseek while chaos on zen
    mock_ks = MagicMock()
    mock_ks.route.side_effect = [
        {"ok": True, "provider": "deepseek", "route": {"provider": "deepseek"}},
        {"ok": True, "provider": "deepseek", "route": {"provider": "deepseek"}},
        {"ok": True, "provider": "deepseek", "route": {"provider": "deepseek"}},
    ]
    with patch("tollgate.get_keys_service", return_value=mock_ks):
        rep = run_failover_test("opencode_zen", requests=3, duration_s=30)

    assert rep["requests_tested"] == 3
    assert rep["successful"] == 3
    assert rep["failed"] == 0
    assert rep["automatic_failover_pct"] == 100.0
    assert rep["survived"] is True
    assert "survived" in (rep.get("message") or "").lower()
    assert is_provider_in_chaos("opencode_zen") is False


def test_resilience_score_shape(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["consumer_envelopes"] = {"desk": {"max_usd_day": 5}}
    cfg["auto_failover"] = True
    cfg["reliability"] = {
        "availability_target": 99.9,
        "max_failover_time_s": 5.0,
        "required_fallbacks": 2,
        "gradual_recovery_s": 0,
    }
    save_config(cfg)

    s = resilience_score()
    assert s["ok"] is True
    assert 0 <= s["score"] <= 100
    assert "reliability" in s["dimensions"]
    assert "failover" in s["dimensions"]
    assert "policy" in s
    assert s["policy"]["required_fallbacks"] == 2
    assert "availability_estimate_pct" in s
    assert isinstance(s["warnings"], list)


def test_gradual_recovery_after_stop(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config
    from tollgate.chaos import is_provider_unavailable, start_chaos, status, stop_chaos

    cfg = load_config(force=True)
    cfg["reliability"] = {"gradual_recovery_s": 120.0}
    save_config(cfg)

    start_chaos("deepseek", duration_s=30)
    stop_chaos("deepseek", start_gradual_recovery=True)
    st = status()
    assert any(r.get("provider") == "deepseek" for r in (st.get("recovering") or []))
    # right after stop, progress ~0 → should divert
    assert is_provider_unavailable("deepseek") is True


def test_failover_report_includes_policy_and_cost(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["reliability"] = {"gradual_recovery_s": 0, "max_failover_time_s": 5.0}
    save_config(cfg)

    mock_ks = MagicMock()
    mock_ks.route.return_value = {
        "ok": True,
        "provider": "deepseek",
        "route": {"provider": "deepseek"},
    }
    with patch("tollgate.get_keys_service", return_value=mock_ks):
        rep = run_failover_test("opencode_zen", requests=2, duration_s=10)
    assert "policy" in rep
    assert "extra_cost_usd" in rep
    assert rep["extra_cost_usd"] == 0.0