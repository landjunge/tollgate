"""Stop-only journal contract: synthetic process admission, no paid/provider use."""
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event

import pytest

from tollgate.workflow_control import AttemptIdentity, ControlError, WorkflowControl, WorkflowScope

SCOPE = WorkflowScope("synthetic-project", "owned-workflow")
IDENTITY = AttemptIdentity(SCOPE, "thread:task", "codex", "codex-lane", "turn-1", "a" * 64)


def control(root, **kwargs):
    return WorkflowControl(root=root, registered_process_actors={"codex": "codex-lane"}, **kwargs)


def test_durable_stop_before_spawn_restart_unknown_and_no_budget_claim(tmp_path):
    c = control(tmp_path)
    assert c.stop(SCOPE, "stop-before")["status"] == "EFFECTIVE"
    with control(tmp_path).process_start(IDENTITY) as permit:
        assert permit["start_allowed"] is False
        assert permit["reason_code"] == "WORKFLOW_STOPPED"
        assert permit["cost_kind"] == "unknown" and permit["hard_cost_cap"] is False
        assert "reserved_microusd" not in permit and "unit" not in permit
    assert control(tmp_path).status(SCOPE)["budgets"] == []
    other = replace(IDENTITY, scope=WorkflowScope("synthetic-project", "other-workflow"))
    with pytest.raises(RuntimeError, match="synthetic-interrupt"):
        with c.process_start(other) as permit:
            assert permit["start_allowed"]
            journal = json.loads(c._path(other.scope).read_text())
            assert journal["attempts"][other.attempt_id]["state"] == "DISPATCH_ATTEMPTED"
            raise RuntimeError("synthetic-interrupt")
    with control(tmp_path).process_start(other) as duplicate:
        assert duplicate["start_allowed"] is False and duplicate["state"] == "OUTCOME_UNKNOWN"


def test_process_lock_covers_actual_spawn_and_registration_not_earlier_token(tmp_path):
    c = control(tmp_path, lock_timeout_s=0.05)
    entered, release = Event(), Event()

    def spawning():
        with c.process_start(IDENTITY) as permit:
            assert permit["start_allowed"]
            entered.set()
            assert release.wait(3)

    with ThreadPoolExecutor(2) as executor:
        start = executor.submit(spawning)
        assert entered.wait(2)
        pending = c.stop(SCOPE, "race-stop")
        assert pending["status"] == "PENDING" and not pending["further_dispatch_blocked"]
        release.set()
        start.result(timeout=3)
    assert c.stop(SCOPE, "race-stop")["status"] == "EFFECTIVE"
    with control(tmp_path).process_start(replace(IDENTITY, attempt_id="turn-2")) as permit:
        assert not permit["start_allowed"]
    original = c.get_attempt(IDENTITY)
    assert original["spawn_observed"] and original["state"] == "OUTCOME_UNKNOWN"
    assert not c.stop(SCOPE, "same-stop")["abort_confirmed"]


def test_no_caller_flag_actor_swap_budget_downgrade_or_mixed_accounting(tmp_path):
    c = control(tmp_path)
    with pytest.raises(ControlError, match="PROCESS_ADAPTER_UNAVAILABLE"):
        with WorkflowControl(root=tmp_path).process_start(IDENTITY):
            pytest.fail("unregistered")
    with pytest.raises(ControlError, match="PROCESS_ADAPTER_UNAVAILABLE"):
        with c.process_start(replace(IDENTITY, consumer_id="another-lane")):
            pytest.fail("swapped lane")
    c.configure_budget(SCOPE, "codex", "codex-lane", 1)
    with pytest.raises(ControlError, match="CONTROL_MODE_CONFLICT"):
        with c.process_start(IDENTITY):
            pytest.fail("bounded scope downgraded")
    scope = WorkflowScope("synthetic-project", "cli-only")
    identity = replace(IDENTITY, scope=scope)
    with c.process_start(identity):
        pass
    with pytest.raises(ControlError, match="CONTROL_MODE_CONFLICT"):
        c.configure_budget(scope, "codex", "codex-lane", 0)
    with pytest.raises(ControlError, match="CONTROL_MODE_CONFLICT"):
        c.settle(identity, 0, "not-billed", "no-evidence")
    with pytest.raises(ControlError, match="IDEMPOTENCY_CONFLICT"):
        with c.process_start(replace(identity, request_hash="b" * 64)):
            pytest.fail("changed request")
    assert c.status(scope)["budgets"] == []
