"""Persistent scope identity; only isolated temporary journals are changed."""
from dataclasses import asdict
import json
import uuid

import pytest

from tollgate.workflow_control import ControlError, WorkflowControl, WorkflowScope

SCOPE = WorkflowScope("synthetic-project", "workflow")


def test_new_identity_is_durable_without_budget_or_stop_change_and_restart_is_read_only(tmp_path):
    control = WorkflowControl(root=tmp_path)
    identity = control.control_identity(SCOPE)
    assert uuid.UUID(hex=identity["journal_id"]).version == 4
    assert identity["scope"] == asdict(SCOPE) and identity["schema"] == 1
    assert identity["source_authenticated"] is False
    path = control._path(SCOPE)
    original = path.read_bytes()
    snapshot = json.loads(original)
    assert snapshot["attempts"] == snapshot["budgets"] == {} and not snapshot["stopped"]
    assert snapshot["seq"] == 1
    assert WorkflowControl(root=tmp_path).control_identity(SCOPE) == identity
    assert path.read_bytes() == original
    assert path.stat().st_mode & 0o777 == 0o600
    assert sorted(p.name for p in path.parent.iterdir()) == sorted([path.name, path.name + ".lock"])


def test_legacy_stopped_budget_journal_gains_identity_once_without_losing_facts(tmp_path):
    control = WorkflowControl(root=tmp_path)
    control.configure_budget(SCOPE, "codex", "codex-lane", 100)
    control.stop(SCOPE, "durable-stop")
    path = control._path(SCOPE)
    old = json.loads(path.read_text())
    old.pop("journal_id")  # Synthetic historical journal from before this field.
    path.write_text(json.dumps(old))
    result = control.control_identity(SCOPE)
    migrated = json.loads(path.read_text())
    for field in ["stopped", "stop_id", "barrier_seq", "budgets", "attempts", "scope", "schema"]:
        assert migrated[field] == old[field]
    assert migrated["seq"] == old["seq"] + 1 and migrated["journal_id"] == result["journal_id"]
    before = path.read_bytes()
    assert control.control_identity(SCOPE) == result and path.read_bytes() == before


def test_recreated_temporary_journal_or_other_root_has_different_identity(tmp_path):
    first = WorkflowControl(root=tmp_path / "first")
    identity = first.control_identity(SCOPE)
    other = WorkflowControl(root=tmp_path / "other").control_identity(SCOPE)
    assert other["journal_id"] != identity["journal_id"]
    first._path(SCOPE).unlink()  # Only the synthetic tmp_path fixture, never real state.
    recreated = first.control_identity(SCOPE)
    assert recreated["journal_id"] not in {identity["journal_id"], other["journal_id"]}


@pytest.mark.parametrize("broken", [None, True, 17, "", "0" * 32, "g" * 32, "a" * 64])
def test_invalid_existing_journal_identity_fails_closed_without_repair_or_reset(tmp_path, broken):
    control = WorkflowControl(root=tmp_path)
    control.control_identity(SCOPE)
    path = control._path(SCOPE)
    data = json.loads(path.read_text())
    data["journal_id"] = broken
    path.write_text(json.dumps(data))
    original = path.read_bytes()
    with pytest.raises(ControlError, match="JOURNAL_UNAVAILABLE"):
        control.control_identity(SCOPE)
    assert path.read_bytes() == original
