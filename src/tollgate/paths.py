"""Tollgate data paths — portable / USB-friendly, no machine-local hardcoding.

Layout options
--------------
1. Env (any machine)::

     TOLLGATE_HOME=/path/to/data   # contains User/Key.txt, keys_app.json, …

2. Portable / USB (repo on stick)::

     /Volumes/STICK/tollgate/          # code (+ optional .venv)
     /Volumes/STICK/WS-tollgate/       # data sibling (preferred if present)
       User/Key.txt
     # or colocated:
     /Volumes/STICK/tollgate/User/Key.txt

3. Desk (default when not portable)::

     ~/.tollgate/User/…

Detection
---------
Portable if any of:
  - TOLLGATE_PORTABLE=1|true|yes
  - code root under /Volumes, /media, /run/media, /mnt
  - sibling WS-tollgate exists
  - colocated User/ next to repo
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_WS_NAME = "WS-tollgate"
USB_PREFIXES = ("/Volumes/", "/media/", "/run/media/", "/mnt/")


def project_root() -> Path:
    """Package / install root (…/tollgate)."""
    # src/tollgate/paths.py → parents[2] = repo root when editable
    return Path(__file__).resolve().parents[2]


def is_usb_path(path: Path | None = None) -> bool:
    """True if path sits on a typical removable mount."""
    base = Path(path) if path is not None else project_root()
    try:
        s = str(base.resolve())
    except OSError:
        s = str(base)
    # normalize for case-insensitive macOS volumes
    low = s.replace("\\", "/")
    return any(low.startswith(p) or low.startswith(p.rstrip("/")) for p in USB_PREFIXES)


def is_portable_mode(root: Path | None = None) -> bool:
    """
    Explicit env, USB mount, or colocated User/ under the repo.

    Note: a sibling WS-tollgate on a normal home disk does *not* alone
    force portable mode (avoids hijacking desk installs).
    """
    flag = (os.environ.get("TOLLGATE_PORTABLE") or "").strip().lower()
    if flag in ("1", "true", "yes", "on", "usb"):
        return True
    if flag in ("0", "false", "no", "off"):
        return False
    hub = Path(root) if root is not None else project_root()
    if is_usb_path(hub):
        return True
    # intentional single-folder portable: secrets next to code
    if (hub / "User").is_dir():
        return True
    # data already pointed at a removable mount
    for env in ("TOLLGATE_HOME", "GNOM_WS"):
        v = (os.environ.get(env) or "").strip()
        if not v:
            continue
        try:
            if is_usb_path(Path(v).expanduser()):
                return True
        except OSError:
            continue
    return False


def portable_data_candidates(root: Path | None = None) -> list[Path]:
    """Ordered candidates when running portable / USB."""
    hub = Path(root) if root is not None else project_root()
    return [
        hub.parent / DEFAULT_WS_NAME,  # sibling WS-tollgate (keeps secrets off code tree)
        hub,  # colocated: tollgate/User/
        hub / "data",
    ]


def resolve_portable_home(root: Path | None = None) -> Path:
    """
    Pick data root for portable mode.

    Prefer existing sibling WS-tollgate or colocated User/, else create sibling WS.
    """
    hub = Path(root) if root is not None else project_root()
    for cand in portable_data_candidates(hub):
        if (cand / "User").is_dir() or (cand / "User" / "Key.txt").is_file():
            return cand.resolve()
    for cand in portable_data_candidates(hub):
        if cand.is_dir() and cand != hub:
            return cand.resolve()
    # default portable: sibling WS next to repo (works when stick is writable)
    sibling = (hub.parent / DEFAULT_WS_NAME).resolve()
    try:
        sibling.mkdir(parents=True, exist_ok=True)
        return sibling
    except OSError:
        # read-only stick root — fall back to colocated under repo
        return hub.resolve()


def data_home() -> Path:
    """
    Root for Key.txt, keys_app.json, keys_usage.json.

    Order:
      1. TOLLGATE_HOME
      2. GNOM_WS (compat while migrating from gnom)
      3. portable/USB layout (sibling WS-tollgate or colocated)
      4. ~/.tollgate
    """
    for env in ("TOLLGATE_HOME", "GNOM_WS"):
        v = (os.environ.get(env) or "").strip()
        if v:
            return Path(v).expanduser().resolve()
    if is_portable_mode():
        return resolve_portable_home()
    return (Path.home() / ".tollgate").resolve()


def user_dir(root: Path | None = None) -> Path:
    """User secrets dir: <data_home>/User"""
    if root is not None:
        return (Path(root) / "User").resolve()
    return (data_home() / "User").resolve()


def personal_workspace(root: Path | None = None) -> Path:
    return data_home() if root is None else Path(root).resolve()


def pin_data_home_env() -> Path:
    """
    Ensure TOLLGATE_HOME is set for child processes / MCP / logging.

    Does not override an already-set TOLLGATE_HOME or GNOM_WS.
    """
    home = data_home()
    if not (os.environ.get("TOLLGATE_HOME") or "").strip():
        # If only GNOM_WS is set, leave it; still export TOLLGATE_HOME for clarity
        if (os.environ.get("GNOM_WS") or "").strip():
            os.environ.setdefault("TOLLGATE_HOME", os.environ["GNOM_WS"])
        else:
            os.environ["TOLLGATE_HOME"] = str(home)
    return home


def path_snapshot() -> dict[str, object]:
    """For /v1/health — no secrets, useful on USB desk."""
    home = data_home()
    return {
        "project_root": str(project_root()),
        "data_home": str(home),
        "user_dir": str(user_dir()),
        "portable": is_portable_mode(),
        "usb": is_usb_path(project_root()) or is_usb_path(home),
        "tollgate_home_env": bool((os.environ.get("TOLLGATE_HOME") or "").strip()),
        "gnom_ws_env": bool((os.environ.get("GNOM_WS") or "").strip()),
    }
