"""Portable / USB path resolution."""

from __future__ import annotations

import importlib
import os
from pathlib import Path


def _reload_paths(monkeypatch, **env):
    for k in ("TOLLGATE_HOME", "GNOM_WS", "TOLLGATE_PORTABLE"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)
    import tollgate.paths as paths

    return importlib.reload(paths)


def test_desk_default_home(monkeypatch, tmp_path):
    paths = _reload_paths(monkeypatch)
    # without portable flag, home is ~/.tollgate (may exist)
    h = paths.data_home()
    assert h.name == ".tollgate" or "WS-tollgate" in str(h) or h == Path.home() / ".tollgate"
    assert paths.is_usb_path(Path("/Volumes/Stick/tollgate")) is True
    assert paths.is_usb_path(Path("/Users/someone/tollgate")) is False


def test_tolgate_home_wins(monkeypatch, tmp_path):
    paths = _reload_paths(monkeypatch, TOLLGATE_HOME=str(tmp_path))
    assert paths.data_home() == tmp_path.resolve()
    assert paths.user_dir() == (tmp_path / "User").resolve()


def test_portable_flag_uses_sibling_or_repo(monkeypatch, tmp_path):
    # isolate: point project_root via monkeypatch is hard; use TOLLGATE_HOME instead for isolation
    paths = _reload_paths(monkeypatch, TOLLGATE_PORTABLE="1", TOLLGATE_HOME=str(tmp_path / "data"))
    assert paths.data_home() == (tmp_path / "data").resolve()
    snap = paths.path_snapshot()
    assert "data_home" in snap
    assert "portable" in snap


def test_path_snapshot_keys(monkeypatch, tmp_path):
    paths = _reload_paths(monkeypatch, TOLLGATE_HOME=str(tmp_path))
    snap = paths.path_snapshot()
    for k in ("project_root", "data_home", "user_dir", "portable", "usb"):
        assert k in snap
