"""Compact desk status + success response headers."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_desk_status_structure(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_FROZEN", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.status import desk_status, format_status_text

    st = desk_status(root=tmp_path)
    assert st["ok"] is True or st["level"] in ("ok", "warn", "error", "frozen")
    assert "freeze" in st
    assert "resilience" in st
    assert "spend" in st
    text = format_status_text(st)
    assert "tollgate status" in text
    assert "freeze" in text


def test_status_http(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c

    c.clear_cache()
    from tollgate.server_v1 import app

    client = TestClient(app)
    r = client.get("/v1/status", headers={"X-Consumer-Key": "desk"})
    assert r.status_code == 200
    assert "level" in r.json()

    t = client.get(
        "/v1/status",
        params={"format": "text"},
        headers={"X-Consumer-Key": "desk"},
    )
    assert t.status_code == 200
    assert "tollgate status" in t.text


def test_response_headers_helper():
    from tollgate.openai_compat import response_headers

    h = response_headers(
        {
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "cache_hit": True,
            "failover": {"hops": 2},
        },
        consumer="n8n",
        requested_model="tollgate/free",
    )
    assert h["X-Tollgate-Provider"] == "deepseek"
    assert h["X-Tollgate-Consumer"] == "n8n"
    assert h["X-Tollgate-Routed-From"] == "tollgate/free"
    assert h["X-Tollgate-Cache"] == "hit"
    assert h["X-Tollgate-Failover-Hops"] == "2"


def test_cli_status(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.cli import main

    main(["status"])
    out = capsys.readouterr().out
    assert "tollgate status" in out
