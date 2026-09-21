"""G4: TollGate emits envelope JSONL without changing admit."""

from __future__ import annotations

import json
from pathlib import Path

from tollgate.gateway.decision import Decision
from tollgate.gateway.errors import ErrorClass


def test_emit_off_under_pytest_by_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("TOLLGATE_AUTHORITY_EVENTS", raising=False)
    monkeypatch.setenv("TOLLGATE_AUTHORITY_EVENTS_PATH", str(tmp_path / "x.jsonl"))
    Decision.allow()
    Decision.deny("nope", code=ErrorClass.BUDGET_HARD)
    assert not (tmp_path / "x.jsonl").exists()


def test_allow_and_budget_deny_jsonl(tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "authority-events.jsonl"
    monkeypatch.setenv("TOLLGATE_AUTHORITY_EVENTS", "1")
    monkeypatch.setenv("TOLLGATE_AUTHORITY_EVENTS_PATH", str(out))
    monkeypatch.setenv("TOLLGATE_WORKFLOW_ID", "tg-wf")
    Decision.allow()
    Decision.deny("over budget", code=ErrorClass.BUDGET_HARD, provider="deepseek", op="chat")
    Decision.deny("admission frozen", code=ErrorClass.POLICY_DENY)
    lines = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert [e["event_type"] for e in lines] == [
        "budget.checked",
        "budget.checked",
        "consumer.frozen",
    ]
    assert lines[0]["decision"] == "ALLOW"
    assert lines[1]["decision"] == "DENY"
    assert lines[2]["decision"] == "FREEZE"
    for ev in lines:
        assert ev["source_tool"] == "tollgate"
        assert ev["workflow_id"] == "tg-wf"
        assert "api_key" not in ev
    assert not list(tmp_path.glob("*.sqlite"))
