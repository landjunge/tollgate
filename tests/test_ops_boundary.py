"""Cache yes / memory no — technical enforcement."""

from __future__ import annotations

from tollgate.gateway.context import RequestClass, RequestContext
from tollgate.ops_boundary import META_DENYLIST, assert_no_memory_fields, sanitize_meta
from tollgate.response_cache import (
    cache_eligible,
    clear as cache_clear,
    get as cache_get,
    make_key,
    put as cache_put,
)
from tollgate.usage_ledger import load_usage, record_usage


def test_sanitize_meta_strips_content():
    raw = {
        "model": "deepseek-v4-flash",
        "content": "user secret wish please remember",
        "message": "hello",
        "prompt": "system: you are",
        "agent_id": "gnom:brainstorm",
        "query": "should not land in ledger",
    }
    clean = sanitize_meta(raw)
    assert "content" not in clean
    assert "message" not in clean
    assert "prompt" not in clean
    assert "query" not in clean
    assert clean.get("model") == "deepseek-v4-flash"
    assert clean.get("agent_id") == "gnom:brainstorm"


def test_record_usage_never_stores_transcript(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    record_usage(
        "deepseek",
        op="chat",
        tokens_in=10,
        tokens_out=5,
        usd=0.01,
        root=tmp_path,
        meta={
            "model": "x",
            "content": "THIS MUST NOT PERSIST",
            "messages": [{"role": "user", "content": "hi"}],
            "consumer": "n8n",
        },
    )
    data = load_usage(root=tmp_path)
    errs = assert_no_memory_fields(data)
    assert not errs, errs
    meta = (data.get("providers") or {}).get("deepseek", {}).get("last_meta") or {}
    assert "content" not in meta
    assert meta.get("consumer") == "n8n"


def test_cache_not_for_interactive():
    ctx = RequestContext(request_class=RequestClass.INTERACTIVE)
    assert cache_eligible("brave", "search", ctx=ctx) is False


def test_cache_for_batch_search(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    cache_clear()
    ctx = RequestContext(request_class=RequestClass.BATCH, agent_id="n8n")
    assert cache_eligible("brave", "search", ctx=ctx) is True
    assert cache_eligible("google", "status", ctx=ctx) is False  # high risk


def test_cache_key_includes_consumer():
    k1 = make_key("brave", "search", {"query": "a", "count": 5}, consumer="n8n")
    k2 = make_key("brave", "search", {"query": "a", "count": 5}, consumer="gnom")
    assert k1 != k2
    cache_clear()
    cache_put(k1, {"ok": True, "results": [1]})
    assert cache_get(k1) is not None
    assert cache_get(k2) is None


def test_denylist_covers_memory_words():
    for w in ("content", "transcript", "wish", "history", "message", "prompt"):
        assert w in META_DENYLIST
    # "chat" is a valid op counter name under by_op — not denylisted
