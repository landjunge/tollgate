"""OpenAI-compatible /v1/chat/completions + /v1/models."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c

    c.clear_cache()
    from tollgate.server_v1 import app

    return TestClient(app)


def test_models_list(client):
    r = client.get("/v1/models", headers={"Authorization": "Bearer desk"})
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "list"
    ids = {m["id"] for m in body["data"]}
    assert "tollgate/auto" in ids or "tollgate/free" in ids


def test_chat_completions_shape(client):
    fake = {
        "ok": True,
        "content": "pong",
        "model": "deepseek-v4-flash-free",
        "provider": "opencode_zen",
        "prompt_tokens": 3,
        "completion_tokens": 1,
    }
    with patch("tollgate.server_v1.routed_chat", return_value=fake):
        r = client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer n8n:ignored-in-open-mode"},
            json={
                "model": "tollgate/free",
                "messages": [{"role": "user", "content": "ping"}],
            },
        )
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["content"] == "pong"
    assert body["usage"]["total_tokens"] == 4
    assert body["tollgate"]["consumer"] in ("n8n", "anonymous", "n8n")


def test_chat_stream_sse(client):
    fake = {
        "ok": True,
        "content": "hello stream world",
        "model": "x",
        "prompt_tokens": 1,
        "completion_tokens": 2,
    }
    with patch("tollgate.server_v1.routed_chat", return_value=fake):
        r = client.post(
            "/v1/chat/completions",
            headers={"X-Consumer-Key": "n8n"},
            json={
                "model": "tollgate/auto",
                "stream": True,
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")
    text = r.text
    assert "data: " in text
    assert "[DONE]" in text


def test_chat_budget_maps_402(client):
    fake = {"ok": False, "error": "max_usd_day exceeded", "error_class": "BUDGET_HARD"}
    with patch("tollgate.server_v1.routed_chat", return_value=fake):
        r = client.post(
            "/v1/chat/completions",
            json={
                "model": "deepseek-v4-flash",
                "messages": [{"role": "user", "content": "x"}],
            },
        )
    assert r.status_code == 402
    assert "error" in r.json()


def test_openapi_includes_chat(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/v1/chat/completions" in paths
    assert "/v1/models" in paths
