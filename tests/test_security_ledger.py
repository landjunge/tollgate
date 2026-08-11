"""Fail-closed ledger, redaction, append-only audit, config POST."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from tollgate.audit_log import append_audit, audit_path
from tollgate.gateway.admit import admit
from tollgate.redact import redact_secrets
from tollgate.usage_ledger import is_ledger_corrupt, load_usage, usage_path


def test_config_post_exists(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c

    c.clear_cache()
    from tollgate.server_v1 import app

    client = TestClient(app)
    r = client.post("/v1/config", json={"prefer_free": True})
    assert r.status_code == 200
    assert r.json().get("ok") is True
    assert client.get("/v1/config").status_code == 200


def test_config_post_rejects_invalid_high_risk(monkeypatch, tmp_path):
    """Live PATCH must not leave invalid keys_app (same checks as startup)."""
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c

    c.clear_cache()
    from tollgate.server_v1 import app

    client = TestClient(app)
    r = client.post(
        "/v1/config",
        json={
            "cost_guard": {"high_risk_providers": ["azure_openai"]},
            "providers": {
                "azure_openai": {"enabled": True, "high_risk": True, "max_usd_day": 0},
            },
        },
    )
    assert r.status_code == 400


def test_redact_bearer_and_sk():
    raw = "Authorization: Bearer sk-supersecretvalue12345 failed"
    out = redact_secrets(raw)
    assert "sk-supersecretvalue12345" not in out
    assert "REDACTED" in out


def test_corrupt_ledger_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    path = usage_path(tmp_path)
    path.write_text("{not valid json!!!", encoding="utf-8")
    data = load_usage(root=tmp_path)
    assert is_ledger_corrupt(data) is True
    d = admit("deepseek", op="chat", tokens_est=100)
    assert d.allowed is False
    assert "fail-closed" in (d.reason or "").lower() or "corrupt" in (d.reason or "").lower()


def test_audit_append_only(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    p = audit_path(tmp_path)
    append_audit("test", provider="x", error="Authorization: Bearer sk-abc1234567890", root=tmp_path)
    append_audit("test2", provider="y", root=tmp_path)
    text = p.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert len(lines) == 2
    assert "sk-abc1234567890" not in text
    assert "REDACTED" in text or "Bearer" in text
