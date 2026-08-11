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


def test_validate_old_config_without_circuits_block():
    """
    Regression (PR #7): legacy keys_app.json has no circuits key.
    Must stay valid and materialize CircuitsModel defaults (0.8/1.2/30s/5).
    """
    old = {
        "version": 2,
        "prefer_free": True,
        "cost_guard": {
            "enabled": True,
            "max_usd_day_global": 5.0,
            "high_risk_providers": ["google"],
        },
        "providers": {
            "deepseek": {"enabled": True, "max_calls_day": 100},
        },
        # deliberately no "circuits"
    }
    data, errs = validate_config_dict(old)
    assert errs == [], errs
    assert data is not None
    circ = data.get("circuits") or {}
    assert float(circ.get("jitter_min")) == 0.8
    assert float(circ.get("jitter_max")) == 1.2
    assert float(circ.get("cooldown_s")) == 30.0
    assert float(circ.get("hard_cooldown_s")) == 300.0
    assert int(circ.get("failure_threshold")) == 5


def test_validate_empty_circuits_object_uses_defaults():
    data, errs = validate_config_dict({"version": 2, "circuits": {}})
    assert errs == []
    assert data is not None
    assert float(data["circuits"]["jitter_min"]) == 0.8
    assert float(data["circuits"]["jitter_max"]) == 1.2


def test_validate_explicit_zero_jitter_rejected():
    data, errs = validate_config_dict(
        {"version": 2, "circuits": {"jitter_min": 0, "jitter_max": 0}}
    )
    # pydantic gt=0 → errors (not silent accept)
    assert data is None or errs
    assert errs


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
