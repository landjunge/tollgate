"""Generic high-risk, soft warn, provider scaffold, alerts."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch


def test_high_risk_from_config(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config
    from tollgate.cost import check_cost_guard, is_high_risk

    cfg = load_config(force=True, root=tmp_path)
    guard = dict(cfg.get("cost_guard") or {})
    guard["high_risk_providers"] = ["google", "azure_openai"]
    cfg["cost_guard"] = guard
    cfg.setdefault("providers", {})["azure_openai"] = {
        "enabled": False,
        "high_risk": True,
        "max_usd_day": 1.0,
    }
    save_config(cfg, root=tmp_path)

    assert is_high_risk("azure_openai") is True
    r = check_cost_guard("azure_openai")
    assert r["allowed"] is False
    assert r["high_risk"] is True


def test_soft_warn_ratio(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config
    from tollgate.cost import check_cost_guard
    from tollgate.usage_ledger import record_usage

    cfg = load_config(force=True, root=tmp_path)
    guard = dict(cfg.get("cost_guard") or {})
    guard["max_usd_day_global"] = 1.0
    guard["soft_warn_ratio"] = 0.5
    guard["soft_warn_remaining_usd"] = 0.01
    cfg["cost_guard"] = guard
    save_config(cfg, root=tmp_path)

    # spend 0.6 USD → 60% of 1.0
    record_usage("deepseek", op="chat", tokens_in=0, tokens_out=0, usd=0.6, root=tmp_path)
    r = check_cost_guard("deepseek")
    assert r["allowed"] is True
    assert r.get("soft_warn") is True


def test_provider_scaffold(tmp_path, monkeypatch):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    from tollgate.provider_scaffold import scaffold_provider
    import tollgate.distill.loader as loader

    # write into real distill dir is ok for unique name then delete
    pid = "zz_scaffold_test_provider"
    path = loader.distill_dir() / f"{pid}.json"
    if path.is_file():
        path.unlink()
    out = scaffold_provider(pid, base_url="https://example.test", high_risk=True)
    assert out["ok"] is True
    assert path.is_file()
    data = json.loads(path.read_text())
    assert data["high_risk"] is True
    assert data["auth"]["env"]
    path.unlink()


def test_alert_skips_without_webhook(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_ALERT_WEBHOOK", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.alerts import clear_alert_cache, maybe_alert

    clear_alert_cache()
    r = maybe_alert("soft_budget", provider="deepseek", message="test")
    assert r.get("skipped") is True


def test_alert_posts(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.setenv("TOLLGATE_ALERT_WEBHOOK", "http://127.0.0.1:9/hook")
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.alerts import clear_alert_cache, maybe_alert

    clear_alert_cache()

    class _Resp:
        def getcode(self):
            return 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    with patch("urllib.request.urlopen", return_value=_Resp()):
        r = maybe_alert("soft_budget", provider="x", message="hi", force=True)
    assert r.get("ok") is True
