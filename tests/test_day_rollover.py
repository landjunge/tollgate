"""Ledger day boundary — self-healing midnight reset without cron."""

from __future__ import annotations

from datetime import date, timedelta
from unittest import mock

from tollgate.usage_ledger import _empty_day, _load_unlocked, _write_unlocked, usage_path


def test_load_rolls_stale_day(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    path = usage_path(tmp_path)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    stale = _empty_day(yesterday)
    stale["totals"]["calls"] = 99
    stale["providers"]["deepseek"] = {"calls": 99, "tokens": 0, "usd": 1.0}
    _write_unlocked(path, stale)

    data = _load_unlocked(path)
    assert data["day"] == date.today().isoformat()
    assert int(data["totals"]["calls"]) == 0
