"""Audit trail query — who was denied and why."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_append_and_query(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.audit_log import (
        append_audit,
        audit_summary,
        query_audit,
        recent_denies,
    )

    append_audit(
        "admit_deny",
        provider="deepseek",
        op="chat",
        consumer="n8n",
        error="agent protection: max_tool_calls",
        ok=False,
        extra={"protection": "max_tool_calls"},
        root=tmp_path,
    )
    append_audit(
        "usage",
        provider="deepseek",
        op="chat",
        consumer="gnom",
        tokens=100,
        usd=0.01,
        ok=True,
        root=tmp_path,
    )
    append_audit(
        "admit_deny",
        provider="brave",
        op="search",
        consumer="n8n",
        error="max_usd_day",
        ok=False,
        extra={"protection": "max_usd_day"},
        root=tmp_path,
    )

    q = query_audit(limit=10, event="admit_deny", root=tmp_path)
    assert q["ok"]
    assert q["count"] == 2
    assert all(e["event"] == "admit_deny" for e in q["events"])

    q2 = query_audit(limit=10, consumer="n8n", root=tmp_path)
    assert q2["count"] == 2

    s = audit_summary(root=tmp_path)
    assert s["admit_denies"] == 2
    assert s["agent_protection_blocks"] >= 1
    assert s["by_event"].get("usage") == 1
    reasons = {r["reason"] for r in s["top_deny_reasons"]}
    assert "max_tool_calls" in reasons or any("tool" in r for r in reasons)

    rd = recent_denies(limit=5, root=tmp_path)
    assert len(rd) == 2
    assert rd[0]["consumer"] == "n8n"


def test_control_includes_recent_denies(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.audit_log import append_audit
    from tollgate.control_plane import control_snapshot

    append_audit(
        "admit_deny",
        provider="deepseek",
        consumer="loop",
        error="agent protection: max_requests_minute",
        ok=False,
        extra={"protection": "max_requests_minute"},
        root=tmp_path,
    )
    snap = control_snapshot(root=tmp_path)
    assert snap["ok"]
    assert "recent_denies" in snap
    assert any(d.get("consumer") == "loop" for d in snap["recent_denies"])
    assert snap["audit"]["admit_denies"] >= 1


def test_audit_http_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c
    from tollgate.audit_log import append_audit

    c.clear_cache()
    append_audit(
        "admit_deny",
        provider="x",
        consumer="desk",
        error="test deny",
        ok=False,
        root=tmp_path,
    )

    from tollgate.server_v1 import app

    client = TestClient(app)
    r = client.get("/v1/audit", headers={"X-Consumer-Key": "desk"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"]
    assert body["count"] >= 1

    s = client.get(
        "/v1/audit",
        params={"summary": "true"},
        headers={"X-Consumer-Key": "desk"},
    )
    assert s.status_code == 200
    assert s.json().get("admit_denies", 0) >= 1


def test_cli_audit(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.audit_log import append_audit
    from tollgate.cli import main

    append_audit(
        "admit_deny",
        consumer="cli",
        error="budget",
        ok=False,
        root=tmp_path,
    )
    main(["audit", "--event", "admit_deny", "--limit", "5"])
    out = capsys.readouterr().out
    assert "admit_deny" in out
    assert "cli" in out
