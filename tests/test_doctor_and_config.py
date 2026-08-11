"""doctor + config validation."""

from __future__ import annotations

from tollgate.config_validate import validate_config_dict
from tollgate.doctor import run_doctor


def test_validate_high_risk_enabled_without_cap():
    cfg = {
        "version": 2,
        "cost_guard": {"high_risk_providers": ["azure_openai"], "max_usd_day_global": 5},
        "providers": {
            "azure_openai": {"enabled": True, "high_risk": True, "max_usd_day": 0},
        },
    }
    _, errs = validate_config_dict(cfg)
    assert any("max_usd_day" in e for e in errs)


def test_validate_ok_default():
    from tollgate.app_config import DEFAULT_CONFIG

    _, errs = validate_config_dict(DEFAULT_CONFIG)
    assert errs == []


def test_doctor_runs(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    r = run_doctor(live=False)
    assert "issues" in r
    assert "summary" in r
    # no Key.txt → error
    assert r["ok"] is False
    assert any(i.get("code") == "no_key_txt" for i in r["issues"])


def test_doctor_with_keyfile(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    ud = tmp_path / "User"
    ud.mkdir(parents=True)
    (ud / "Key.txt").write_text(
        "DEEPSEEK_API_KEY=sk-live-doctor-check-key-ok99\n", encoding="utf-8"
    )
    r = run_doctor(live=False)
    assert any("DEEPSEEK" in x for x in r.get("ok_items") or []), r


def test_doctor_flags_missing_chaos_and_fallbacks(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    ud = tmp_path / "User"
    ud.mkdir(parents=True)
    (ud / "Key.txt").write_text("DEEPSEEK_API_KEY=sk-live-doctor-check-key-ok99\n", encoding="utf-8")
    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["reliability"] = {
        "required_fallbacks": 3,
        "max_failover_time_s": 5,
        "gradual_recovery_s": 0,
    }
    # only one free_llm provider enabled effectively
    cfg["routing"] = dict(cfg.get("routing") or {})
    cfg["routing"]["intents"] = {"free_llm": ["opencode_zen"], "llm": ["deepseek"]}
    provs = dict(cfg.get("providers") or {})
    provs["opencode_zen"] = dict(provs.get("opencode_zen") or {}, enabled=True)
    provs["deepseek"] = dict(provs.get("deepseek") or {}, enabled=True)
    # disable others so free_llm has only 1
    for pid in list(provs.keys()):
        if pid not in ("opencode_zen", "deepseek"):
            provs[pid] = dict(provs.get(pid) or {}, enabled=False)
    cfg["providers"] = provs
    save_config(cfg)

    r = run_doctor(live=False)
    codes = {i.get("code") for i in r.get("issues") or []}
    assert "chaos_untested" in codes or "policy_fallbacks" in codes
