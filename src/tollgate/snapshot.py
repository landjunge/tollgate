"""
Desk snapshot export / import — portable migration without guessing paths.

  tollgate snapshot export -o desk.tgz
  tollgate snapshot import desk.tgz
  tollgate snapshot import desk.tgz --dry-run

Never includes Key.txt unless --include-secrets (explicit).
Ops only: config, consumers (hashes), ledger, circuits, chaos, optional audit.
"""

from __future__ import annotations

import io
import json
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tollgate.paths import data_home, path_snapshot, pin_data_home_env, user_dir

SNAPSHOT_VERSION = 1
META_NAME = "snapshot_meta.json"

# Relative to User/
_CORE_FILES = (
    "keys_app.json",
    "consumers.json",
    "keys_usage.json",
    "circuits.json",
    "chaos.json",
)
_OPTIONAL_FILES = (
    "audit.jsonl",
    "agent_rates.json",  # agent_guard short windows if present
)


def _user(root: Path | None = None) -> Path:
    return user_dir(root)


def _safe_name(name: str) -> bool:
    # only flat User/ files — no path traversal
    if not name or "/" in name or "\\" in name or name.startswith("."):
        return False
    return name.replace("_", "").replace(".", "").replace("-", "").isalnum() or name.endswith(
        (".json", ".jsonl", ".txt")
    )


def export_snapshot(
    dest: str | Path,
    *,
    include_secrets: bool = False,
    include_audit: bool = True,
    root: Path | None = None,
) -> dict[str, Any]:
    """
    Write a ``.tgz`` (or ``.tar.gz``) archive of desk ops state.

    Returns meta summary. Secrets (Key.txt) only with ``include_secrets=True``.
    """
    pin_data_home_env()
    ud = _user(root)
    dest_p = Path(dest).expanduser().resolve()
    if dest_p.suffix not in (".tgz", ".gz") and not str(dest_p).endswith(".tar.gz"):
        dest_p = dest_p.with_suffix(dest_p.suffix + ".tgz") if dest_p.suffix else Path(str(dest_p) + ".tgz")

    files: list[str] = []
    skipped: list[str] = []
    for name in _CORE_FILES:
        p = ud / name
        if p.is_file():
            files.append(name)
        else:
            skipped.append(name)

    if include_audit:
        for name in _OPTIONAL_FILES:
            if (ud / name).is_file():
                files.append(name)

    secrets_included = False
    if include_secrets:
        for name in ("Key.txt", ".env"):
            if (ud / name).is_file():
                files.append(name)
                secrets_included = True

    meta = {
        "snapshot_version": SNAPSHOT_VERSION,
        "product": "tollgate",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "ts": time.time(),
        "files": files,
        "skipped_missing": skipped,
        "include_secrets": secrets_included,
        "portable": path_snapshot(),
        "data_home": str(data_home()),
        "notes": (
            "Import with: tollgate snapshot import <file>. "
            "Key.txt is omitted unless export used --include-secrets."
        ),
    }

    dest_p.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(dest_p, "w:gz") as tar:
        # meta first
        raw = json.dumps(meta, indent=2, ensure_ascii=False).encode("utf-8")
        info = tarfile.TarInfo(name=META_NAME)
        info.size = len(raw)
        info.mtime = int(time.time())
        tar.addfile(info, io.BytesIO(raw))

        for name in files:
            path = ud / name
            if not path.is_file():
                continue
            tar.add(path, arcname=f"User/{name}")

    return {
        "ok": True,
        "path": str(dest_p),
        "files": files,
        "include_secrets": secrets_included,
        "bytes": dest_p.stat().st_size if dest_p.is_file() else 0,
        "meta": meta,
    }


def _read_tar_members(archive: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    meta: dict[str, Any] = {}
    blobs: dict[str, bytes] = {}
    with tarfile.open(archive, "r:gz") as tar:
        for m in tar.getmembers():
            if not m.isfile():
                continue
            name = m.name.lstrip("./")
            f = tar.extractfile(m)
            if f is None:
                continue
            data = f.read()
            if name == META_NAME or name.endswith("/" + META_NAME):
                try:
                    meta = json.loads(data.decode("utf-8"))
                except Exception:  # noqa: BLE001
                    meta = {}
                continue
            # User/foo or just foo
            base = name.split("/")[-1]
            if not _safe_name(base):
                continue
            if base == META_NAME:
                continue
            blobs[base] = data
    return meta, blobs


def import_snapshot(
    source: str | Path,
    *,
    dry_run: bool = False,
    replace: bool = False,
    root: Path | None = None,
) -> dict[str, Any]:
    """
    Import desk snapshot into current ``TOLLGATE_HOME`` User/.

    - ``replace=False`` (default): only write files that are missing, except
      keys_app.json is deep-merged onto existing when both exist.
    - ``replace=True``: overwrite listed files from archive.
    - Never auto-overwrite Key.txt unless archive contains it *and* replace=True
      or destination Key.txt missing.
    """
    pin_data_home_env()
    src = Path(source).expanduser().resolve()
    if not src.is_file():
        return {"ok": False, "error": f"snapshot not found: {src}"}

    meta, blobs = _read_tar_members(src)
    ud = _user(root)
    planned: list[dict[str, str]] = []
    applied: list[str] = []

    for name, data in blobs.items():
        dest = ud / name
        action = "write"
        if dest.is_file() and not replace:
            if name == "keys_app.json":
                action = "merge"
            elif name == "Key.txt":
                action = "skip_exists_secret"
            else:
                action = "skip_exists"
        planned.append({"file": name, "action": action, "bytes": str(len(data))})

        if dry_run:
            continue
        if action == "skip_exists" or action == "skip_exists_secret":
            continue

        ud.mkdir(parents=True, exist_ok=True)
        if action == "merge" and dest.is_file():
            try:
                cur = json.loads(dest.read_text(encoding="utf-8"))
                if not isinstance(cur, dict):
                    cur = {}
            except Exception:  # noqa: BLE001
                cur = {}
            try:
                over = json.loads(data.decode("utf-8"))
                if not isinstance(over, dict):
                    over = {}
            except Exception:  # noqa: BLE001
                over = {}
            from tollgate.app_config import _deep_merge, save_config

            merged = _deep_merge(cur, over)
            save_config(merged, root=root)
            applied.append(name)
            continue

        dest.write_bytes(data)
        applied.append(name)

    # clear caches so next load sees disk
    if not dry_run and applied:
        try:
            from tollgate import app_config, consumers
            from tollgate.gateway.circuit import reset_circuits_for_tests

            app_config._CACHE = None
            app_config._CACHE_MTIME = None
            consumers.clear_cache()
            reset_circuits_for_tests()
        except Exception as e:  # noqa: BLE001
            from tollgate.soft_fail import soft_fail

            soft_fail("snapshot_cache_clear", e)

    return {
        "ok": True,
        "dry_run": dry_run,
        "replace": replace,
        "source": str(src),
        "user_dir": str(ud),
        "meta": meta,
        "planned": planned,
        "applied": applied if not dry_run else [],
        "files_in_archive": sorted(blobs.keys()),
    }


def snapshot_info(source: str | Path) -> dict[str, Any]:
    """List archive contents without importing."""
    src = Path(source).expanduser().resolve()
    if not src.is_file():
        return {"ok": False, "error": f"not found: {src}"}
    meta, blobs = _read_tar_members(src)
    return {
        "ok": True,
        "path": str(src),
        "meta": meta,
        "files": sorted(blobs.keys()),
        "sizes": {k: len(v) for k, v in blobs.items()},
    }
