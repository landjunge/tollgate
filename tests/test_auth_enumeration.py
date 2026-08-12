"""GET /v1/auth must not enumerate consumers when auth is required."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tollgate.consumers import add_consumer, clear_cache
from tollgate.server_v1 import app


def test_auth_public_hides_consumers_when_required(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    clear_cache()
    add_consumer("desk", secret="super-secret-desk-key", admin=True)
    clear_cache()

    client = TestClient(app)
    r = client.get("/v1/auth")
    assert r.status_code == 200
    body = r.json()
    assert body.get("required") is True
    assert "consumers" not in body
    assert "consumers_n" not in body

    # authenticated gets details
    r2 = client.get(
        "/v1/auth",
        headers={"X-Consumer-Key": "desk:super-secret-desk-key"},
    )
    assert r2.status_code == 200
    b2 = r2.json()
    assert b2.get("required") is True
    assert "consumers" in b2
    assert b2.get("viewer") == "desk"
