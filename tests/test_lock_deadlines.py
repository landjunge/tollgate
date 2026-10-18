"""Bounded local control remains bounded across invalid values and wall-clock changes."""
import pytest

from tollgate.filelock import FileLock
from tollgate.workflow_control import ControlError, WorkflowControl


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), -1, 0, True, "1", 10**10000, 31], ids=["nan", "inf", "negative", "zero", "bool", "string", "huge", "overmax"])
def test_control_rejects_unbounded_wait_before_state_access(tmp_path, timeout):
    with pytest.raises(ControlError, match="INVALID_LOCK_TIMEOUT"):
        WorkflowControl(root=tmp_path, lock_timeout_s=timeout)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), -1, True, "1", 10**10000], ids=["nan", "inf", "negative", "bool", "string", "huge"])
def test_file_lock_rejects_invalid_deadline_without_opening(tmp_path, timeout):
    with pytest.raises(ValueError):
        FileLock(tmp_path / "journal", timeout_s=timeout)
    assert list(tmp_path.iterdir()) == []


def test_contended_deadline_uses_monotonic_time_and_closes_descriptor(tmp_path, monkeypatch):
    from tollgate import filelock

    ticks = iter([100.0, 100.2])
    monkeypatch.setattr(filelock.time, "monotonic", lambda: next(ticks))

    def no_wall_clock():
        raise AssertionError("deadline must not depend on adjusted wall clock")

    monkeypatch.setattr(filelock.time, "time", no_wall_clock)
    lock = FileLock(tmp_path / "journal", timeout_s=.1)
    monkeypatch.setattr(lock, "_lock", lambda: (_ for _ in ()).throw(BlockingIOError()))
    with pytest.raises(TimeoutError):
        lock.__enter__()
    assert lock._fh is None
