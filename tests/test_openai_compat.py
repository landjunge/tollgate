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


def test_route_flattens_provider():
    from tollgate import get_keys_service

    # nested primary is flattened by KeysService.route
    with patch("tollgate.service.route_intent") as ri:
        ri.return_value = {
            "ok": True,
            "route": {"provider": "nvidia", "model": "x", "base_url": "https://n"},
            "fallbacks": [],
        }
        r = get_keys_service().route("free_llm")
    assert r.get("provider") == "nvidia"
    assert r.get("model") == "x"


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
    """Synthetic fallback path when force_synthetic or non-stream provider."""
    fake = {
        "ok": True,
        "mode": "synthetic",
        "provider": "opencode_zen",
        "stream": iter(
            [
                'data: {"id":"c1","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant"}}]}\n\n',
                'data: {"id":"c1","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"hi"}}]}\n\n',
                "data: [DONE]\n\n",
            ]
        ),
    }
    with patch("tollgate.chat_stream.start_chat_stream", return_value=fake):
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
    assert r.headers.get("X-Tollgate-Stream") == "synthetic"


def test_upstream_stream_chunks(monkeypatch, tmp_path):
    """Real stream path: admit + mocked upstream SSE → client SSE + ledger."""
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_STREAM_SYNTHETIC", raising=False)
    (tmp_path / "User").mkdir(parents=True)

    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    # ensure deepseek enabled for admit
    provs = dict(cfg.get("providers") or {})
    provs["deepseek"] = dict(provs.get("deepseek") or {}, enabled=True)
    cfg["providers"] = provs
    save_config(cfg)

    events = [
        {
            "ok": True,
            "data": {
                "id": "up1",
                "choices": [{"index": 0, "delta": {"content": "Hel"}, "finish_reason": None}],
            },
        },
        {
            "ok": True,
            "data": {
                "id": "up1",
                "choices": [{"index": 0, "delta": {"content": "lo"}, "finish_reason": None}],
            },
        },
        {
            "ok": True,
            "data": {
                "id": "up1",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            },
        },
        {"ok": True, "done": True},
    ]

    with patch("tollgate.chat_stream.can_upstream_stream", return_value=True), patch(
        "tollgate.chat_stream._build_upstream",
        return_value={
            "url": "https://example.test/v1/chat/completions",
            "headers": {"Authorization": "Bearer x"},
            "body": {"model": "deepseek-v4-flash", "stream": True},
            "model": "deepseek-v4-flash",
        },
    ), patch("tollgate.httputil.iter_sse_json", return_value=iter(events)):
        from tollgate.chat_stream import start_chat_stream

        started = start_chat_stream(
            [{"role": "user", "content": "hi"}],
            provider="deepseek",
            model="deepseek-v4-flash",
            consumer="n8n",
            agent_id="n8n",
        )
        assert started["ok"] is True
        assert started["mode"] == "upstream"
        text = "".join(started["stream"])
    assert "Hel" in text
    assert "lo" in text
    assert "[DONE]" in text
    assert "stream_mode" in text or "upstream" in text

    from tollgate.usage_ledger import consumer_usage

    cu = consumer_usage("n8n")
    assert cu["calls"] >= 1
    assert cu["tokens"] >= 5


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
