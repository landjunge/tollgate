"""Ledger + circuit concurrency / multi-worker persistence."""

from __future__ import annotations

import concurrent.futures
import os
from pathlib import Path

from tollgate.gateway.circuit import CircuitRegistry, reset_circuits_for_tests
from tollgate.usage_ledger import load_usage, record_usage, usage_path


def test_ledger_thread_safe_writes(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    n = 40

    def one(i: int) -> None:
        record_usage("deepseek", op="chat", tokens_in=1, tokens_out=1, usd=0.001, root=tmp_path)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(one, range(n)))

    data = load_usage(root=tmp_path)
    assert int((data.get("totals") or {}).get("calls") or 0) == n
    assert int((data.get("providers") or {}).get("deepseek", {}).get("calls") or 0) == n


def test_circuit_persists_across_registry(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    reset_circuits_for_tests()

    r1 = CircuitRegistry(root=tmp_path, persist=True)
    for _ in range(5):
        r1.failure("brave", message="429")
    snap1 = r1.snapshot()
    assert any(c.get("state") == "open" for c in snap1)

    # new process-like registry loads from disk
    r2 = CircuitRegistry(root=tmp_path, persist=True)
    snap2 = r2.snapshot()
    assert any(c.get("provider") == "brave" and c.get("state") == "open" for c in snap2)
    assert r2.allow("brave") is False

    reset_circuits_for_tests()


def test_ledger_path_under_home(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    p = usage_path(tmp_path)
    assert p.parent == (tmp_path / "User").resolve()
