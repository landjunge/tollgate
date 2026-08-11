"""Anthropic-compatible POST /v1/messages."""

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


def test_messages_shape(client):
    fake = {
        "ok": True,
        "content": "hello anthro",
        "model": "deepseek-v4-flash-free",
        "provider": "opencode_zen",
        "prompt_tokens": 4,
        "completion_tokens": 2,
    }
    with patch("tollgate.server_v1.routed_chat", return_value=fake):
        r = client.post(
            "/v1/messages",
            headers={
                "x-api-key": "desk",
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-sonnet-4-0",
                "max_tokens": 64,
                "system": "Be brief.",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "message"
    assert body["role"] == "assistant"
    assert body["content"][0]["type"] == "text"
    assert body["content"][0]["text"] == "hello anthro"
    assert body["usage"]["input_tokens"] == 4
    assert body["usage"]["output_tokens"] == 2
    assert body["tollgate"]["consumer"] in ("desk", "anonymous")
    # non-silent rewrite of claude-* alias
    assert body["tollgate"].get("routed_from") == "claude-sonnet-4-0"
    assert body["tollgate"].get("routed_to") == "deepseek-v4-flash-free"

def test_messages_content_blocks(client):
    fake = {
        "ok": True,
        "content": "ok",
        "prompt_tokens": 1,
        "completion_tokens": 1,
    }
    with patch("tollgate.server_v1.routed_chat", return_value=fake) as rc:
        r = client.post(
            "/v1/messages",
            headers={"x-api-key": "n8n"},
            json={
                "model": "claude-sonnet-4-0",
                "max_tokens": 32,
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": "ping"}],
                    }
                ],
            },
        )
    assert r.status_code == 200
    # claude-* should clear model for router
    args = rc.call_args
    assert args is not None
    # messages include text
    msgs = args[0][0]
    assert any(m.get("content") == "ping" for m in msgs)


def test_messages_budget_maps_error(client):
    fake = {"ok": False, "error": "max_usd_day exceeded", "error_class": "BUDGET_HARD"}
    with patch("tollgate.server_v1.routed_chat", return_value=fake):
        r = client.post(
            "/v1/messages",
            headers={"Authorization": "Bearer desk"},
            json={
                "model": "tollgate/auto",
                "max_tokens": 16,
                "messages": [{"role": "user", "content": "x"}],
            },
        )
    assert r.status_code == 402
    body = r.json()
    assert body["type"] == "error"
    assert "error" in body


def test_messages_stream_sse(client):
    fake = {
        "ok": True,
        "mode": "synthetic",
        "provider": "opencode_zen",
        "model": "x",
        "stream": iter(
            [
                'data: {"id":"c1","choices":[{"index":0,"delta":{"role":"assistant"}}]}\n\n',
                'data: {"id":"c1","choices":[{"index":0,"delta":{"content":"Hi"}}]}\n\n',
                'data: {"id":"c1","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],'
                '"usage":{"prompt_tokens":1,"completion_tokens":1}}\n\n',
                "data: [DONE]\n\n",
            ]
        ),
    }
    with patch("tollgate.chat_stream.start_chat_stream", return_value=fake):
        r = client.post(
            "/v1/messages",
            headers={"x-api-key": "desk"},
            json={
                "model": "tollgate/free",
                "max_tokens": 32,
                "stream": True,
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")
    assert r.headers.get("X-Tollgate-Compat") == "anthropic"
    text = r.text
    assert "event: message_start" in text
    assert "event: content_block_delta" in text
    assert "Hi" in text
    assert "event: message_stop" in text


def test_normalize_system_and_blocks():
    from tollgate.anthropic_compat import normalize_anthropic_messages

    msgs = normalize_anthropic_messages(
        [{"role": "user", "content": [{"type": "text", "text": "a"}]}],
        system="sys",
    )
    assert msgs[0] == {"role": "system", "content": "sys"}
    assert msgs[1]["content"] == "a"


def test_openapi_includes_messages(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/v1/messages" in paths
