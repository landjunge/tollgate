"""Actual lock-bound identity guard; all journal replacement is temporary/synthetic."""
from dataclasses import replace
import json

import pytest

from tollgate.workflow_control import AttemptIdentity, ControlError, WorkflowControl, WorkflowScope

SCOPE = WorkflowScope("synthetic-project", "owned-workflow")
IDENTITY = AttemptIdentity(SCOPE, "thread:task", "codex", "codex-lane", "turn1", "a" * 64)


def control(root):
    return WorkflowControl(root=root, registered_process_actors={"codex": "codex-lane"})


def test_swap_after_earlier_identity_check_cannot_start_or_report_effective_stop(tmp_path):
    c = control(tmp_path)
    earlier = c.control_identity(SCOPE)["journal_id"]
    c.stop(SCOPE, "before-swap", expected_journal_id=earlier)
    path = c._path(SCOPE)
    path.unlink()  # Simulate replacement after the caller's earlier check, in tmp_path only.
    later = c.control_identity(SCOPE)["journal_id"]
    assert earlier != later
    untouched = path.read_bytes()
    with pytest.raises(ControlError, match="JOURNAL_IDENTITY_CHANGED"):
        with c.process_start(IDENTITY, expected_journal_id=earlier):
            pytest.fail("dispatch into a replaced journal")
    with pytest.raises(ControlError, match="JOURNAL_IDENTITY_CHANGED"):
        c.stop(SCOPE, "after-swap", expected_journal_id=earlier)
    assert path.read_bytes() == untouched
    data = json.loads(untouched)
    assert data["attempts"] == {} and not data["stopped"]


def test_missing_expected_journal_does_not_create_one_and_legacy_scope_only_callers_still_work(tmp_path):
    c = control(tmp_path)
    expected = c.control_identity(SCOPE)["journal_id"]
    path = c._path(SCOPE)
    path.unlink()
    with pytest.raises(ControlError, match="JOURNAL_IDENTITY_CHANGED"):
        with c.process_start(IDENTITY, expected_journal_id=expected):
            pytest.fail("missing bound journal")
    with pytest.raises(ControlError, match="JOURNAL_IDENTITY_CHANGED"):
        c.stop(SCOPE, "missing-journal", expected_journal_id=expected)
    assert not path.exists()
    # Old explicit callers did not claim an epoch identity: API remains compatible.
    with c.process_start(IDENTITY) as receipt:
        assert receipt["start_allowed"] and not receipt["hard_cost_cap"]
    assert c.stop(SCOPE, "legacy-scope-only")["status"] == "EFFECTIVE"
    assert c.control_identity(SCOPE)["journal_id"] != expected


def test_matching_identity_orders_actual_start_and_stop_and_preserves_unknown_attempt(tmp_path):
    c = control(tmp_path)
    expected = c.control_identity(SCOPE)["journal_id"]
    with c.process_start(IDENTITY, expected_journal_id=expected) as receipt:
        assert receipt["start_allowed"]
        data = json.loads(c._path(SCOPE).read_text())
        assert data["journal_id"] == expected
        assert data["attempts"][IDENTITY.attempt_id]["state"] == "DISPATCH_ATTEMPTED"
    assert c.stop(SCOPE, "matching-stop", expected_journal_id=expected)["status"] == "EFFECTIVE"
    with c.process_start(replace(IDENTITY, attempt_id="turn2"), expected_journal_id=expected) as receipt:
        assert not receipt["start_allowed"] and receipt["reason_code"] == "WORKFLOW_STOPPED"
    assert c.get_attempt(IDENTITY)["state"] == "OUTCOME_UNKNOWN"
    assert c.control_identity(SCOPE)["journal_id"] == expected


@pytest.mark.parametrize("invalid", [True, "", "0" * 32, "g" * 32, 17])
def test_invalid_expected_identity_fails_before_persisting_start_or_stop(tmp_path, invalid):
    c = control(tmp_path)
    with pytest.raises(ControlError, match="INVALID_JOURNAL_IDENTITY"):
        with c.process_start(IDENTITY, expected_journal_id=invalid):
            pytest.fail("invalid expected identity")
    with pytest.raises(ControlError, match="INVALID_JOURNAL_IDENTITY"):
        c.stop(SCOPE, "invalid-identity", expected_journal_id=invalid)
    assert not c._path(SCOPE).exists()
