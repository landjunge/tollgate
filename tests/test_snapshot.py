"""Desk snapshot export / import."""

from __future__ import annotations

import json
from pathlib import Path


def test_export_import_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    ud = tmp_path / "User"
    ud.mkdir(parents=True)
    (ud / "keys_app.json").write_text(
        json.dumps(
            {
                "version": 2,
                "prefer_free": True,
                "consumer_envelopes": {"n8n": {"max_usd_day": 1.5}},
            }
        ),
        encoding="utf-8",
    )
    (ud / "keys_usage.json").write_text(
        json.dumps({"day": "2099-01-01", "totals": {"calls": 3, "usd": 0.1}}),
        encoding="utf-8",
    )
    (ud / "Key.txt").write_text("DEEPSEEK_API_KEY=sk-secret-should-not-export\n", encoding="utf-8")
    (ud / "audit.jsonl").write_text(
        json.dumps({"event": "admit_deny", "consumer": "n8n"}) + "\n",
        encoding="utf-8",
    )

    from tollgate.snapshot import export_snapshot, import_snapshot, snapshot_info

    arch = tmp_path / "out" / "desk.tgz"
    exp = export_snapshot(arch, include_secrets=False, include_audit=True, root=tmp_path)
    assert exp["ok"]
    assert arch.is_file()
    assert "Key.txt" not in exp["files"]
    assert "keys_app.json" in exp["files"]
    assert "audit.jsonl" in exp["files"]

    info = snapshot_info(arch)
    assert info["ok"]
    assert "keys_app.json" in info["files"]
    assert "Key.txt" not in info["files"]

    # import into a fresh home
    home2 = tmp_path / "home2"
    home2.mkdir()
    monkeypatch.setenv("TOLLGATE_HOME", str(home2))
    from tollgate import app_config

    app_config._CACHE = None
    app_config._CACHE_MTIME = None

    plan = import_snapshot(arch, dry_run=True, root=home2)
    assert plan["ok"]
    assert plan["dry_run"] is True
    assert any(p["file"] == "keys_app.json" for p in plan["planned"])

    done = import_snapshot(arch, dry_run=False, root=home2)
    assert done["ok"]
    assert "keys_app.json" in done["applied"]
    cfg = json.loads((home2 / "User" / "keys_app.json").read_text(encoding="utf-8"))
    assert float(cfg["consumer_envelopes"]["n8n"]["max_usd_day"]) == 1.5
    assert not (home2 / "User" / "Key.txt").is_file()


def test_export_can_include_secrets(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    ud = tmp_path / "User"
    ud.mkdir(parents=True)
    (ud / "keys_app.json").write_text('{"version":2}', encoding="utf-8")
    (ud / "Key.txt").write_text("X=1\n", encoding="utf-8")
    from tollgate.snapshot import export_snapshot, snapshot_info

    arch = tmp_path / "sec.tgz"
    exp = export_snapshot(arch, include_secrets=True, root=tmp_path)
    assert exp["include_secrets"] is True
    assert "Key.txt" in exp["files"]
    info = snapshot_info(arch)
    assert "Key.txt" in info["files"]


def test_cli_snapshot(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    ud = tmp_path / "User"
    ud.mkdir(parents=True)
    (ud / "keys_app.json").write_text('{"version":2,"prefer_free":true}', encoding="utf-8")
    from tollgate.cli import main

    arch = tmp_path / "cli.tgz"
    try:
        main(["snapshot", "export", "-o", str(arch)])
    except SystemExit as e:
        assert e.code in (0, None)
    out = json.loads(capsys.readouterr().out)
    assert out["ok"]
    main(["snapshot", "info", str(arch)])
    info = json.loads(capsys.readouterr().out)
    assert info["ok"]
