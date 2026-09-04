"""A snapshot is untrusted input; importing one must not change routing silently.

`keys_app.json` carries provider entries, and a provider's `base_url` decides
where real requests go — with the API key attached. If a foreign archive can
deep-merge that file just by being imported, then "portable desk migrate" is
also a key-exfiltration primitive: point a provider at your own host, wait for
the next call.

The operator must therefore opt in (`--merge-config`) or overwrite outright
(`--replace`). Plain `tollgate snapshot import` leaves local config alone.
"""

from __future__ import annotations

import json
import tarfile
from io import BytesIO
from pathlib import Path

import pytest

HONEST_CONFIG = {
    "providers": {
        "opencode_zen": {"base_url": "https://api.opencode.example", "enabled": True}
    },
    "cost_guard": {"soft_warn_ratio": 0.8},
}

HOSTILE_CONFIG = {
    "providers": {
        "opencode_zen": {"base_url": "https://attacker.example/collect", "enabled": True}
    },
    "cost_guard": {"soft_warn_ratio": 1.0},
}

EXFIL_URL = "https://attacker.example/collect"


def _write_snapshot(path: Path, config: dict) -> None:
    payload = json.dumps(config).encode("utf-8")
    with tarfile.open(path, "w:gz") as tar:
        info = tarfile.TarInfo(name="User/keys_app.json")
        info.size = len(payload)
        tar.addfile(info, BytesIO(payload))


@pytest.fixture
def desk(tmp_path, monkeypatch):
    """A desk that already has honest local config."""
    home = tmp_path / "home"
    (home / "User").mkdir(parents=True)
    (home / "User" / "keys_app.json").write_text(json.dumps(HONEST_CONFIG), encoding="utf-8")
    monkeypatch.setenv("TOLLGATE_HOME", str(home))

    archive = tmp_path / "foreign.tgz"
    _write_snapshot(archive, HOSTILE_CONFIG)
    return home, archive


def _local_base_url(home: Path) -> str:
    cfg = json.loads((home / "User" / "keys_app.json").read_text(encoding="utf-8"))
    return cfg["providers"]["opencode_zen"]["base_url"]


def test_plain_import_does_not_touch_local_config(desk):
    from tollgate.snapshot import import_snapshot

    home, archive = desk
    result = import_snapshot(archive)

    assert result.get("ok") is not False
    assert _local_base_url(home) != EXFIL_URL, (
        "importing a foreign snapshot rewrote a provider base_url without consent"
    )
    assert _local_base_url(home) == "https://api.opencode.example"


def test_plan_names_the_skipped_config_explicitly(desk):
    """The operator should be able to see that config was left alone."""
    from tollgate.snapshot import import_snapshot

    _, archive = desk
    result = import_snapshot(archive, dry_run=True)
    actions = {row["file"]: row["action"] for row in result.get("planned", [])}
    assert actions.get("keys_app.json") == "skip_exists_config"


def test_merge_config_opt_in_still_works(desk):
    from tollgate.snapshot import import_snapshot

    home, archive = desk
    import_snapshot(archive, merge_config=True)
    assert _local_base_url(home) == EXFIL_URL, "explicit --merge-config must still merge"


def test_replace_still_overwrites(desk):
    from tollgate.snapshot import import_snapshot

    home, archive = desk
    import_snapshot(archive, replace=True)
    assert _local_base_url(home) == EXFIL_URL


def test_archive_paths_are_flattened_not_traversed(tmp_path, monkeypatch):
    """Existing protection, pinned so it cannot regress."""
    from tollgate.snapshot import _read_tar_members

    archive = tmp_path / "evil.tgz"
    payload = b"pwned"
    with tarfile.open(archive, "w:gz") as tar:
        for name in ("../../../../etc/cron.d/evil", "User/../../Key.txt"):
            info = tarfile.TarInfo(name=name)
            info.size = len(payload)
            tar.addfile(info, BytesIO(payload))

    _meta, blobs = _read_tar_members(archive)
    assert "Key.txt" not in blobs
    assert blobs == {}
    for key in blobs:
        assert "/" not in key and "\\" not in key and not key.startswith("..")
