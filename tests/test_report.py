"""Daily operator report + richer deny error metadata."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_build_report_structure(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.audit_log import append_audit
    from tollgate.report import build_report, format_report_markdown
    from tollgate.usage_ledger import record_usage

    record_usage("deepseek", op="chat", tokens_in=10, tokens_out=5, usd=0.02, consumer="n8n")
    append_audit(
        "admit_deny",
        provider="deepseek",
        consumer="n8n",
        error="agent protection: max_tool_calls",
        ok=False,
        extra={"protection": "max_tool_calls"},
        root=tmp_path,
    )

    r = build_report(root=tmp_path)
    assert r["ok"]
    assert r["kind"] == "daily_operator_report"
    assert "protect" in r["pillars"]
    assert "route" in r["pillars"]
    assert "prove" in r["pillars"]
    assert r["pillars"]["protect"]["admit_denies"] >= 1
    md = format_report_markdown(r)
    assert "Tollgate daily report" in md
    assert "Protect" in md
    assert "Prove" in md


def test_report_http_md(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c

    c.clear_cache()
    from tollgate.server_v1 import app

    client = TestClient(app)
    r = client.get("/v1/report", params={"format": "md"}, headers={"X-Consumer-Key": "desk"})
    assert r.status_code == 200
    assert "Tollgate daily report" in r.text
    assert "text/markdown" in r.headers.get("content-type", "")

    j = client.get("/v1/report", headers={"X-Consumer-Key": "desk"})
    assert j.status_code == 200
    assert j.json()["ok"] is True
    assert "pillars" in j.json()


def test_map_tollgate_error_includes_meta_and_headers():
    from tollgate.openai_compat import map_tollgate_error

    body, status, headers = map_tollgate_error(
        {
            "ok": False,
            "error": "agent protection: consumer n8n max_requests_minute",
            "error_class": "POLICY_DENY",
            "provider": "deepseek",
            "admit": {
                "code": "POLICY_DENY",
                "limits": {
                    "protection": "max_requests_minute",
                    "wait_ms": 2500,
                },
                "context": {"consumer": "n8n"},
            },
        }
    )
    assert status == 429
    assert body["error"]["tollgate"]["protection"] == "max_requests_minute"
    assert body["error"]["tollgate"]["error_class"] == "POLICY_DENY"
    assert headers.get("Retry-After") in ("2", "3")  # 2500ms → 2s
    assert headers.get("X-Tollgate-Protection") == "max_requests_minute"
    assert headers.get("X-Tollgate-Error-Class") == "POLICY_DENY"


def test_cli_report(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.cli import main

    main(["report", "--format", "md"])
    out = capsys.readouterr().out
    assert "Tollgate daily report" in out
