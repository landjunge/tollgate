"""Repo search — modules, docs, routes findable without path guessing."""

from __future__ import annotations

from tollgate.repo_search import (
    CLI_COMMANDS,
    HTTP_ROUTES,
    all_entries,
    format_search_text,
    map_markdown,
    search,
)


def test_search_circuit_finds_gateway_circuit():
    r = search("circuit breaker")
    assert r["ok"]
    assert r["hits"]
    paths = " ".join(h["path"] for h in r["hits"][:8])
    assert "circuit" in paths


def test_search_openai_finds_compat_and_docs():
    r = search("openai chat")
    paths = [h["path"] for h in r["hits"]]
    joined = " ".join(paths)
    assert "openai_compat" in joined or "OPENAI" in joined


def test_search_http_kind():
    r = search("/v1/messages", kinds=["http"])
    assert r["hits"]
    assert all(h["kind"] == "http" for h in r["hits"])
    assert any("messages" in h["title"] for h in r["hits"])


def test_search_cli_kind():
    r = search("chaos", kinds=["cli"])
    assert r["hits"]
    assert any(h.get("command") == "chaos" or "chaos" in h["title"] for h in r["hits"])


def test_search_empty_no_crash():
    r = search("")
    assert r["ok"]
    assert r["hits"] == [] or isinstance(r["hits"], list)


def test_search_no_match_exit_shape():
    r = search("zzzxxyyzz_not_a_real_symbol_999")
    assert r["ok"]
    assert r["total_matched"] == 0
    assert r["hits"] == []
    text = format_search_text(r)
    assert "No hits" in text or "0/" in text


def test_map_markdown_has_core_sections():
    md = map_markdown()
    assert "# Tollgate repo map" in md
    assert "HTTP" in md
    assert "/v1/chat/completions" in md
    assert "tollgate search" in md
    assert "agent_guard" in md or "agent protection" in md.lower()


def test_all_entries_cover_kinds():
    kinds = {e.kind for e in all_entries()}
    assert "concept" in kinds
    assert "module" in kinds
    assert "http" in kinds
    assert "cli" in kinds


def test_http_and_cli_tables_nonempty():
    assert len(HTTP_ROUTES) >= 10
    assert any(c["cmd"] == "search" for c in CLI_COMMANDS)


def test_cli_search_runs(capsys):
    from tollgate.cli import main

    try:
        main(["search", "budget", "--limit", "5"])
    except SystemExit as e:
        assert e.code in (0, None)
    out = capsys.readouterr().out
    assert "budget" in out.lower() or "hits" in out.lower() or "[" in out
