"""G02 / V07–09: synthetic effects only; no provider calls or real credentials."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import multiprocessing
import threading

import pytest

from tollgate.workflow_control import AttemptIdentity, ControlError, Quote, WorkflowControl, WorkflowScope

SCOPE = WorkflowScope("project-a", "workflow-a")
QUOTE = Quote("dummy-v1", "dummy", "bounded-send", "local-dummy", 60, "fixed-v1")


def identity(n="a", **changes):
    return replace(AttemptIdentity(SCOPE, "task:1", "codex", "codex-lane", n, "a" * 64), **changes)


def control(root, **changes):
    return WorkflowControl(root=root, admission=lambda *_: True,
                           registered_quotes={QUOTE.adapter_id: QUOTE}, **changes)


def setup(root, amount=100):
    c = control(root)
    c.configure_budget(SCOPE, "codex", "codex-lane", amount)
    return c


def test_concurrent_reservations_and_independent_ai_lanes(tmp_path):
    c = setup(tmp_path)
    c.configure_budget(SCOPE, "grok", "grok-lane", 100)
    with ThreadPoolExecutor(2) as pool:
        states = list(pool.map(lambda n: control(tmp_path).reserve(identity(n), QUOTE)["state"], ["a", "b"]))
    assert sorted(states) == ["DENIED", "RESERVED"]
    assert c.status(SCOPE)["budgets"][0]["reserved"] == 60
    assert c.reserve(identity("c", actor_id="grok", consumer_id="grok-lane"), QUOTE)["state"] == "RESERVED"
    with pytest.raises(ControlError, match="BUDGET_LANE_CONFLICT"):
        c.reserve(identity("d", consumer_id="alternate-key"), QUOTE)
    with pytest.raises(ControlError, match="BUDGET_LANE_CONFLICT"):
        c.configure_budget(SCOPE, "codex", "alternate-key", 100)
    with pytest.raises(ControlError, match="NOT_AUTHORIZED"):
        c.configure_budget(SCOPE, "codex", "codex-lane", 101)


def _reserve_process(root, name, output):
    output.put(control(root).reserve(identity(name), QUOTE)["state"])


def test_cross_process_atomicity(tmp_path):
    setup(tmp_path)
    context = multiprocessing.get_context("spawn")
    output = context.Queue()
    processes = [context.Process(target=_reserve_process, args=(tmp_path, name, output)) for name in ("a", "b")]
    for process in processes:
        process.start()
    for process in processes:
        process.join(10)
        assert process.exitcode == 0
    assert sorted([output.get(timeout=2), output.get(timeout=2)]) == ["DENIED", "RESERVED"]


def test_stop_before_dispatch_and_persistent_barrier(tmp_path):
    c = setup(tmp_path)
    c.reserve(identity(), QUOTE)
    stopped = c.stop(SCOPE, "stop-1")
    assert stopped["status"] == "EFFECTIVE" and stopped["further_dispatch_blocked"]
    calls = []
    assert control(tmp_path).dispatch(identity(), lambda: calls.append(1))["state"] == "CANCELLED_NO_SEND"
    assert not calls
    assert control(tmp_path).reserve(identity("b"), QUOTE)["reason_code"] == "WORKFLOW_STOPPED"
    assert control(tmp_path).status(SCOPE)["budgets"][0]["reserved"] == 0
    assert not control(tmp_path).stop(SCOPE, "stop-2")["abort_confirmed"]


def test_stop_during_send_is_pending_not_false_termination(tmp_path):
    c = setup(tmp_path)
    c.reserve(identity(), QUOTE)
    entered, release = threading.Event(), threading.Event()
    def send():
        entered.set()
        assert release.wait(3)
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(c.dispatch, identity(), send)
        assert entered.wait(2)
        assert control(tmp_path, lock_timeout_s=.04).stop(SCOPE, "stop-1")["status"] == "PENDING"
        # Other workflow can be stopped without waiting for the active network path.
        assert control(tmp_path).stop(WorkflowScope("project-a", "other"), "stop-other")["status"] == "EFFECTIVE"
        release.set()
        assert future.result(2)["state"] == "OUTCOME_UNKNOWN"
    stopped = c.stop(SCOPE, "stop-1")
    assert stopped["status"] == "EFFECTIVE" and stopped["external_effect"] == "unknown"
    assert not stopped["abort_confirmed"]


def test_unknown_timeout_restart_day_rollover_never_replays_or_releases(tmp_path, monkeypatch):
    c = setup(tmp_path)
    c.reserve(identity(), QUOTE)
    calls = []
    def send():
        calls.append(1)
        raise TimeoutError("synthetic-secret-must-not-appear")
    assert c.dispatch(identity(), send)["state"] == "OUTCOME_UNKNOWN"
    monkeypatch.setattr("tollgate.usage_ledger._today", lambda: "2099-01-01")
    restarted = control(tmp_path)
    restarted.reserve(identity(), QUOTE)
    restarted.dispatch(identity(), send)
    assert calls == [1]
    assert restarted.status(SCOPE)["budgets"][0]["reserved"] == 60
    assert "synthetic-secret" not in (tmp_path / "User" / "audit.jsonl").read_text()
    assert "a" * 64 not in (tmp_path / "User" / "audit.jsonl").read_text()


def test_crash_marker_is_unknown_and_never_replayed(tmp_path):
    c = setup(tmp_path)
    c.reserve(identity(), QUOTE)
    # Simulate power loss after persistent marker and before transport response.
    with c._transaction(SCOPE) as (path, data):
        data["attempts"]["a"]["state"] = "DISPATCH_ATTEMPTED"
        c._commit(path, data)
    calls = []
    assert control(tmp_path).dispatch(identity(), lambda: calls.append(1))["state"] == "OUTCOME_UNKNOWN"
    assert not calls
    assert control(tmp_path).status(SCOPE)["budgets"][0]["reserved"] == 60


def test_same_id_changed_hash_or_foreign_scope_cannot_access_attempt(tmp_path):
    c = setup(tmp_path)
    c.reserve(identity(), QUOTE)
    with pytest.raises(ControlError, match="IDEMPOTENCY_CONFLICT"):
        c.reserve(identity(request_hash="b" * 64), QUOTE)
    with pytest.raises(ControlError, match="IDEMPOTENCY_CONFLICT"):
        c.get_attempt(identity(actor_id="someone-else"))
    with pytest.raises(ControlError, match="ATTEMPT_NOT_FOUND"):
        c.get_attempt(identity(scope=WorkflowScope("foreign-project", "workflow-a")))
    assert "request_hash" not in json.dumps(c.status(SCOPE))


def test_final_cost_evidence_idempotent_and_over_quote_incident(tmp_path):
    c = setup(tmp_path)
    c.reserve(identity(), QUOTE)
    with pytest.raises(ControlError, match="SETTLEMENT_NOT_ALLOWED"):
        c.settle(identity(), 40, "bill-1", "receipt-1")
    c.dispatch(identity(), lambda: "NOT_A_BILL")
    c.settle(identity(), 40, "bill-1", "receipt-1")
    c.settle(identity(), 40, "bill-1", "receipt-1")
    assert c.status(SCOPE)["budgets"][0]["spent"] == 40
    with pytest.raises(ControlError, match="SETTLEMENT_CONFLICT"):
        c.settle(identity(), 41, "bill-1", "receipt-1")
    c.reserve(identity("b"), QUOTE)
    c.dispatch(identity("b"), lambda: None)
    assert c.settle(identity("b"), 65, "bill-2", "receipt-2")["reason_code"] == "ACCOUNTING_MISMATCH"
    assert c.status(SCOPE)["budgets"][0]["spent"] == 105
    assert c.reserve(identity("c"), QUOTE)["reason_code"] == "ACCOUNTING_MISMATCH"


@pytest.mark.parametrize("amount", [True, 1.5, -1, 10**16, "10"])
def test_money_strict_integer_and_bounded(tmp_path, amount):
    with pytest.raises(ControlError, match="INVALID_AMOUNT"):
        setup(tmp_path, amount)


def test_quote_only_from_trusted_registered_adapter_and_denial_tombstone(tmp_path):
    c = setup(tmp_path)
    fake = replace(QUOTE, max_cost_microusd=1)
    assert c.reserve(identity(), fake)["reason_code"] == "UNBOUNDED_COST"
    with pytest.raises(ControlError, match="IDEMPOTENCY_CONFLICT"):
        c.reserve(identity(), QUOTE)
    assert c.reserve(identity(), fake)["state"] == "DENIED"


def test_corrupt_journal_fails_closed_and_rechecks_admission(tmp_path):
    c = setup(tmp_path)
    c.reserve(identity(), QUOTE)
    closed = WorkflowControl(root=tmp_path, admission=lambda *_: False, registered_quotes={QUOTE.adapter_id: QUOTE})
    calls = []
    assert closed.dispatch(identity(), lambda: calls.append(1))["state"] == "CANCELLED_NO_SEND"
    assert not calls
    c._path(SCOPE).write_text("{bad-json")
    with pytest.raises(ControlError, match="JOURNAL_UNAVAILABLE"):
        c.status(SCOPE)
