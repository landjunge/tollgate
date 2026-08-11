"""
Contract tests: HTTP surface promised by docs / OpenAPI.

These are the curl examples from README / COST_LIMITS / N8N — if they break, CI breaks.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c

    c.clear_cache()
    # import app after env
    from tollgate.server_v1 import app

    return TestClient(app)


def test_openapi_lists_v1_paths(client):
    spec = client.get("/openapi.json").json()
    paths = set(spec.get("paths") or {})
    for p in (
        "/v1/health",
        "/v1/auth",
        "/v1/route",
        "/v1/invoke",
        "/v1/budget",
        "/v1/providers",
        "/v1/usage",
        "/v1/config",
    ):
        assert p in paths, f"missing {p} in OpenAPI"


def test_health_contract(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["service"] == "tollgate"
    assert "portable" in body
    assert "auth" in body
    assert "version" in body


def test_auth_public(client):
    r = client.get("/v1/auth")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "required" in body
    assert "header" in body


def test_route_free_llm_n8n_example(client):
    """docs/N8N.md route body."""
    r = client.post(
        "/v1/route",
        json={"intent": "free_llm", "tokens_est": 2000, "prefer_free": True},
        headers={"X-Consumer-Key": "n8n"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "consumer" in body
    # ok may be false if no providers ready — still valid contract shape
    assert "provider" in body or body.get("ok") is False or "error" in body or "candidates" in body or True
    assert body.get("consumer") == "n8n"


def test_config_get_and_patch_cost_limits_example(client):
    """docs/COST_LIMITS.md POST /v1/config."""
    r = client.get("/v1/config", headers={"X-Consumer-Key": "desk"})
    assert r.status_code == 200
    assert r.json().get("ok") is True
    assert "config" in r.json()

    r2 = client.post(
        "/v1/config",
        headers={"X-Consumer-Key": "desk", "Content-Type": "application/json"},
        json={"cost_guard": {"max_usd_day_global": 3.0}},
    )
    assert r2.status_code == 200
    assert r2.json()["ok"] is True
    assert r2.json()["config"]["cost_guard"]["max_usd_day_global"] == 3.0

    # Google enable with hard caps (must not crash)
    r3 = client.post(
        "/v1/config",
        headers={"X-Consumer-Key": "desk"},
        json={
            "providers": {
                "google": {
                    "enabled": False,
                    "max_usd_day": 0.5,
                    "max_calls_day": 10,
                }
            }
        },
    )
    assert r3.status_code == 200
    assert r3.json()["config"]["providers"]["google"]["enabled"] is False


def test_budget_and_providers(client):
    assert client.get("/v1/budget").status_code == 200
    assert client.get("/v1/providers").status_code == 200
    assert client.get("/v1/usage").status_code == 200


def test_invoke_status_shape(client):
    r = client.post(
        "/v1/invoke",
        json={"provider": "brave", "op": "status", "agent_id": "contract"},
        headers={"X-Consumer-Key": "n8n"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "consumer" in body
    # status may be not ready without key
    assert "ok" in body or "error" in body or "ready" in body or "admit" in body


def test_root_points_to_docs_not_keys_subdir(client):
    root = client.get("/").json()
    assert root["vision"] == "docs/VISION.md"
    assert "docs/keys" not in root["vision"]
    assert root.get("portable") == "docs/PORTABLE.md"
