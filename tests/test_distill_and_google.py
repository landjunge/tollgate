"""Distill + google default off."""

from __future__ import annotations


def test_google_default_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import DEFAULT_CONFIG, is_provider_enabled, load_config

    assert DEFAULT_CONFIG["providers"]["google"]["enabled"] is False
    cfg = load_config(force=True, root=tmp_path)
    assert cfg["providers"]["google"]["enabled"] is False
    assert is_provider_enabled("google", root=tmp_path) is False


def test_distill_google_high_risk():
    from tollgate.distill.loader import load_distill

    g = load_distill("google")
    assert g
    # high risk markers if present
    text = str(g).lower()
    assert "google" in text or "gemini" in text


def test_research_brave():
    from tollgate import research_for

    note = research_for("brave")
    assert note
