"""Consumer auth (open vs hashed secrets)."""

from __future__ import annotations

import json

import pytest


def test_open_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    from tollgate import consumers as c

    c.clear_cache()
    assert c.auth_required() is False
    v = c.verify_consumer(None)
    assert v["ok"] is True
    assert v["mode"] == "open"
    assert v["admin"] is True


def test_add_and_verify(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    from tollgate import consumers as c

    c.clear_cache()
    (tmp_path / "User").mkdir(parents=True)
    out = c.add_consumer("n8n", secret="s3cret-test-value", admin=False)
    assert out["ok"] is True
    assert out["secret"] == "s3cret-test-value"
    c.clear_cache()
    assert c.auth_required() is True
    bad = c.verify_consumer("n8n:wrong")
    assert bad["ok"] is False
    good = c.verify_consumer("n8n:s3cret-test-value")
    assert good["ok"] is True
    assert good["consumer"] == "n8n"
    admin_needed = c.verify_consumer("n8n:s3cret-test-value", need_admin=True)
    assert admin_needed["ok"] is False


def test_admin_consumer(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    from tollgate import consumers as c

    c.clear_cache()
    (tmp_path / "User").mkdir(parents=True)
    c.add_consumer("desk", secret="admin-secret", admin=True)
    c.clear_cache()
    v = c.verify_consumer("desk:admin-secret", need_admin=True)
    assert v["ok"] is True
    assert v["admin"] is True


def test_http_auth_gate(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c

    c.clear_cache()
    c.add_consumer("n8n", secret="tok", admin=False)
    c.clear_cache()

    from fastapi.testclient import TestClient
    from tollgate.server_v1 import app

    client = TestClient(app)
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json()["auth"]["required"] is True

    r2 = client.post("/v1/route", json={"intent": "free_llm"})
    assert r2.status_code == 401

    r3 = client.post(
        "/v1/route",
        json={"intent": "free_llm"},
        headers={"X-Consumer-Key": "n8n:tok"},
    )
    assert r3.status_code == 200
    assert r3.json().get("consumer") == "n8n"

    r4 = client.get("/v1/config", headers={"X-Consumer-Key": "n8n:tok"})
    assert r4.status_code == 401  # not admin
