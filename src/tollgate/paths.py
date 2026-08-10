"""Tollgate data paths — independent of Gnom-Hub."""

from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    """Package / install root (…/tollgate)."""
    return Path(__file__).resolve().parents[2]


def data_home() -> Path:
    """
    Root for Key.txt, keys_app.json, keys_usage.json.

    Order:
      1. TOLLGATE_HOME
      2. GNOM_WS (compat while migrating from gnom)
      3. ~/.tollgate
    """
    for env in ("TOLLGATE_HOME", "GNOM_WS"):
        v = (os.environ.get(env) or "").strip()
        if v:
            return Path(v).expanduser().resolve()
    return (Path.home() / ".tollgate").resolve()


def user_dir(root: Path | None = None) -> Path:
    """User secrets dir: <data_home>/User"""
    base = Path(root) if root is not None else data_home()
    # if root is project_root, still prefer data_home for secrets
    if root is None:
        return (data_home() / "User").resolve()
    # explicit root (tests)
    return (base / "User").resolve()


def personal_workspace(root: Path | None = None) -> Path:
    return data_home() if root is None else Path(root).resolve()
