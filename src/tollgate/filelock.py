"""Cross-process exclusive file lock (Unix fcntl; Windows msvcrt)."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from types import TracebackType
from typing import IO


class FileLock:
    """Context manager: exclusive lock on ``path`` (+ ``.lock`` sidecar)."""

    def __init__(self, path: Path, *, timeout_s: float = 10.0) -> None:
        self.path = Path(path)
        self.lock_path = self.path.with_name(self.path.name + ".lock")
        self.timeout_s = timeout_s
        self._fh: IO[str] | None = None

    def __enter__(self) -> FileLock:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.lock_path, "a+", encoding="utf-8")
        deadline = time.time() + self.timeout_s
        while True:
            try:
                self._lock()
                return self
            except OSError:
                if time.time() >= deadline:
                    raise TimeoutError(f"lock timeout: {self.lock_path}")
                time.sleep(0.02)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            self._unlock()
        finally:
            if self._fh is not None:
                try:
                    self._fh.close()
                except OSError:
                    pass
                self._fh = None

    def _lock(self) -> None:
        assert self._fh is not None
        if sys.platform == "win32":
            import msvcrt

            self._fh.seek(0)
            msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(self) -> None:
        if self._fh is None:
            return
        try:
            if sys.platform == "win32":
                import msvcrt

                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
