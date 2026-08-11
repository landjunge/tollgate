"""End-to-end: corrupt ledger → check_limits deny → admit deny."""

from __future__ import annotations

import json

from tollgate.gateway.admit import admit
from tollgate.gateway.context import RequestContext
from tollgate.limits import check_limits


def test_corrupt_ledger_blocks_admission(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    ud = tmp_path / "User"
    ud.mkdir(parents=True)
    # corrupt keys_usage.json
    (ud / "keys_usage.json").write_text("{not valid json", encoding="utf-8")

    from tollgate import app_config

    app_config._CACHE = None

    lim = check_limits("deepseek", op="chat", consumer="n8n", tokens_est=10)
    assert lim["allowed"] is False
    assert lim.get("ledger_corrupt") is True
    assert "fail-closed" in (lim.get("reason") or "").lower()

    d = admit(
        "deepseek",
        op="chat",
        tokens_est=10,
        ctx=RequestContext(consumer="n8n"),
    )
    assert d.allowed is False
    assert "ledger" in (d.reason or "").lower() or "fail-closed" in (d.reason or "").lower()


def test_valid_empty_ledger_not_corrupt(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    ud = tmp_path / "User"
    ud.mkdir(parents=True)
    (ud / "keys_usage.json").write_text(
        json.dumps({"day": "2099-01-01", "totals": {}, "providers": {}, "consumers": {}}),
        encoding="utf-8",
    )
    from tollgate import app_config
    from tollgate.usage_ledger import is_ledger_corrupt, load_usage

    app_config._CACHE = None
    day = load_usage(root=tmp_path)
    assert not is_ledger_corrupt(day)
