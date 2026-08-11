"""Structured webhook alerts schema v1."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_build_payload_schema():
    from tollgate.alerts import build_alert_payload, event_catalog

    p = build_alert_payload(
        "agent_protection",
        provider="deepseek",
        message="max_tool_calls",
        extra={"consumer": "n8n", "protection": "max_tool_calls"},
    )
    assert p["schema_version"] == 1
    assert p["service"] == "tollgate"
    assert p["event"] == "agent_protection"
    assert p["severity"] == "error"
    assert p["consumer"] == "n8n"
    assert p["protection"] == "max_tool_calls"
    assert "iso" in p

    cat = event_catalog()
    names = {e["event"] for e in cat["events"]}
    assert "webhook_test" in names
    assert "chaos_dr_failed" in names


def test_test_webhook_posts(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.setenv("TOLLGATE_ALERT_WEBHOOK", "http://example.test/hook")
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.alerts import clear_alert_cache, test_webhook

    clear_alert_cache()
    mock_resp = MagicMock()
    mock_resp.getcode.return_value = 200
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp) as uo:
        r = test_webhook(message="probe")
        assert r["ok"] is True
        assert r["event"] == "webhook_test"
        assert uo.called
        req = uo.call_args[0][0]
        import json

        body = json.loads(req.data.decode("utf-8"))
        assert body["schema_version"] == 1
        assert body["event"] == "webhook_test"
        assert req.get_header("X-tollgate-event") or req.headers.get("X-Tollgate-Event")


def test_alerts_http(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    monkeypatch.delenv("TOLLGATE_ALERT_WEBHOOK", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c

    c.clear_cache()
    from tollgate.server_v1 import app

    client = TestClient(app)
    r = client.get("/v1/alerts", headers={"X-Consumer-Key": "desk"})
    assert r.status_code == 200
    assert r.json()["ok"]
    assert any(e["event"] == "soft_budget" for e in r.json()["events"])

    # no webhook → test fails soft
    t = client.post("/v1/alerts/test", headers={"X-Consumer-Key": "desk"})
    assert t.status_code == 200
    assert t.json().get("ok") is False


def test_cli_alert_events(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.cli import main

    main(["alert", "events"])
    out = capsys.readouterr().out
    assert "webhook_test" in out
