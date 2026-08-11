"""AI Reliability Report scorecard."""

from __future__ import annotations

from tollgate.certificate import build_certificate, format_certificate_text


def test_certificate_structure(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_FROZEN", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    # ensure protect signals
    cfg["consumer_envelopes"] = {
        "_default": {"max_usd_day": 5, "max_tool_calls": 20},
        "support-agent": {"max_usd_day": 2, "max_tool_calls": 20},
    }
    save_config(cfg)

    c = build_certificate(application="Customer Support Agent", root=tmp_path)
    assert c["title"] == "AI RELIABILITY REPORT"
    assert c["application"] == "Customer Support Agent"
    ids = {x["id"]: x["status"] for x in c["checks"]}
    assert ids["budget_protection"] == "PASS"
    assert ids["agent_loop_protection"] == "PASS"
    assert ids["provider_failover"] in ("PASS", "FAIL", "NOT_RUN")
    text = format_certificate_text(c)
    assert "TOLLGATE" in text
    assert "Budget Protection" in text
    assert "Resilience Score" in text


def test_cli_certificate(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.cli import main

    try:
        main(["certificate", "--application", "Test Agent"])
    except SystemExit as e:
        assert e.code in (0, 1, None)
    out = capsys.readouterr().out
    assert "AI RELIABILITY" in out or "TOLLGATE" in out
