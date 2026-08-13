"""Complete code revive — extraction leftovers, fail-closed protect, public root."""

from __future__ import annotations


def test_diagnose_live_uses_registry_not_openrouter_mod(monkeypatch, tmp_path):
    """M9 leftover: diagnose(live=True) used undefined openrouter_mod (NameError)."""
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)

    from tollgate.service import KeysService

    ks = KeysService()
    monkeypatch.setattr(
        ks,
        "inventory",
        lambda live=True, use_cache=True: {"providers": [], "grades": {}},
    )
    monkeypatch.setattr("tollgate.service.recommend_model_route", lambda *a, **k: {})

    def fake_get_ops(pid):
        if pid == "openrouter":
            return {
                "credits": lambda **_kw: {
                    "tried": [{"ok": False, "alias": "dead-key"}]
                }
            }
        return {}

    monkeypatch.setattr("tollgate.service.get_ops", fake_get_ops)
    out = ks.diagnose(live=True)
    assert out.get("ok") is True
    issues = out.get("issues") or []
    assert any("dead key" in str(i.get("issue") or "") for i in issues)


def test_diagnose_live_does_not_nameerror_without_mock(monkeypatch, tmp_path):
    """Real registry path — must not raise NameError even if credits() is a no-op."""
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.service import KeysService

    ks = KeysService()
    monkeypatch.setattr(
        ks,
        "inventory",
        lambda live=True, use_cache=True: {"providers": [], "grades": {}},
    )
    monkeypatch.setattr("tollgate.service.recommend_model_route", lambda *a, **k: {})
    out = ks.diagnose(live=True)
    assert out.get("ok") is True
    assert "issues" in out


def test_root_product_name_not_overwritten(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import consumers as c

    c.clear_cache()
    from fastapi.testclient import TestClient
    from tollgate.server_v1 import app

    root = TestClient(app).get("/").json()
    assert root["product"] == "Tollgate"
    assert root["product_doc"] == "docs/PRODUCT.md"
    assert root["vision"] == "docs/VISION.md"


def test_chat_route_scope_exception_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)

    def boom(*_a, **_k):
        raise RuntimeError("envelope broken")

    monkeypatch.setattr("tollgate.limits.check_consumer_scope", boom)
    from tollgate.chat_route import routed_chat

    out = routed_chat("hi", consumer="agent-x", provider="deepseek")
    assert out.get("ok") is False
    assert out.get("protection") == "scope"
    assert "fail-closed" in str(out.get("error") or "")


def test_chat_stream_scope_exception_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)

    def boom(*_a, **_k):
        raise RuntimeError("envelope broken")

    monkeypatch.setattr("tollgate.limits.check_consumer_scope", boom)
    from tollgate.chat_stream import start_chat_stream

    out = start_chat_stream("hi", consumer="agent-x", provider="deepseek")
    assert out.get("ok") is False
    assert out.get("protection") == "scope"
    assert "fail-closed" in str(out.get("error") or "")


def test_doctor_live_maps_diagnose_fields(monkeypatch, tmp_path):
    """diagnose() uses severity/issue; doctor must not dump the whole dict."""
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    (tmp_path / "User" / "Key.txt").write_text("DEEPSEEK_API_KEY=sk-test-not-real\n")

    class _Fake:
        def diagnose(self, *, live=True):
            return {
                "ok": True,
                "issues": [
                    {
                        "severity": "error",
                        "provider": "openrouter",
                        "issue": "not ready",
                    }
                ],
            }

    monkeypatch.setattr("tollgate.get_keys_service", lambda: _Fake())
    from tollgate.doctor import run_doctor

    report = run_doctor(live=True)
    live_issues = [
        i
        for i in (report.get("issues") or [])
        if i.get("code") == "openrouter" or "not ready" in str(i.get("message") or "")
    ]
    assert live_issues, report.get("issues")
    row = live_issues[0]
    assert row["level"] == "error"
    assert row["message"] == "not ready"
    assert "{" not in row["message"]


def test_audit_facade_returns_events_dict(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.audit import query_audit

    out = query_audit(limit=5)
    assert isinstance(out, dict)
    assert "events" in out
    assert isinstance(out["events"], list)
    # must not be list(dict.keys()) from the old facade
    assert "ok" not in out["events"]


def test_soft_fail_audit_false_does_not_write(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    called = []

    def boom(*_a, **_k):
        called.append(True)
        raise AssertionError("append_audit must not run when audit=False")

    monkeypatch.setattr("tollgate.audit_log.append_audit", boom)
    from tollgate.soft_fail import reset_soft_fail_counts, soft_fail, soft_fail_counts

    reset_soft_fail_counts()
    soft_fail("metrics_circuits", RuntimeError("x"), audit=False)
    assert soft_fail_counts().get("metrics_circuits") == 1
    assert called == []
    reset_soft_fail_counts()


def test_corrupt_consumers_json_fail_closed(monkeypatch, tmp_path):
    """Existing but unreadable consumers.json must not drop into open mode."""
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    user = tmp_path / "User"
    user.mkdir(parents=True)
    (user / "consumers.json").write_text("{not-json", encoding="utf-8")

    from tollgate import consumers as c

    c.clear_cache()
    assert c.consumers_corrupt() is True
    assert c.auth_required() is True
    denied = c.verify_consumer("desk:anything")
    assert denied.get("ok") is False
    assert denied.get("mode") == "auth"
    assert "corrupt" in str(denied.get("error") or "").lower()
    st = c.auth_status()
    assert st.get("corrupt") is True
    assert st.get("required") is True

    # Recovery: consumer-add rewrites a valid file
    out = c.add_consumer("desk", secret="recover-secret", admin=True)
    assert out.get("ok") is True
    c.clear_cache()
    assert c.consumers_corrupt() is False
    ok = c.verify_consumer("desk:recover-secret")
    assert ok.get("ok") is True


def test_health_version_matches_package(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    (tmp_path / "User").mkdir(parents=True)
    from tollgate import __version__, consumers as c

    c.clear_cache()
    from fastapi.testclient import TestClient
    from tollgate.server_v1 import app

    h = TestClient(app).get("/v1/health").json()
    assert h["version"] == __version__


def test_corrupt_keys_app_fail_closed_freeze(monkeypatch, tmp_path):
    """Unreadable keys_app.json must freeze admission, not silently use defaults."""
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_FROZEN", raising=False)
    monkeypatch.delenv("TOLLGATE_ADMISSION_FROZEN", raising=False)
    user = tmp_path / "User"
    user.mkdir(parents=True)
    (user / "keys_app.json").write_text("{not-json", encoding="utf-8")

    from tollgate.app_config import config_corrupt, load_config
    from tollgate.freeze import freeze_status, is_frozen
    from tollgate.gateway.admit import admit
    from tollgate.gateway.context import RequestContext

    load_config(force=True)
    assert config_corrupt() is True
    assert is_frozen() is True
    st = freeze_status()
    assert st.get("source") == "config_corrupt"
    assert st.get("frozen") is True

    d = admit("deepseek", op="chat", tokens_est=10, ctx=RequestContext(consumer="x"))
    assert d.allowed is False
    assert d.limits.get("protection") == "freeze"


def test_missing_keys_app_is_not_corrupt(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.app_config import config_corrupt, load_config
    from tollgate.freeze import is_frozen

    load_config(force=True)
    assert config_corrupt() is False
    assert is_frozen() is False


def test_corrupt_circuits_json_fail_closed(monkeypatch, tmp_path):
    """Unreadable circuits.json must deny hops, not treat as all-closed."""
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    user = tmp_path / "User"
    user.mkdir(parents=True)
    (user / "circuits.json").write_text("{not-json", encoding="utf-8")

    from tollgate.gateway.circuit import (
        circuits_corrupt,
        get_circuits,
        reset_circuits,
        reset_circuits_for_tests,
    )
    from tollgate.gateway.admit import admit
    from tollgate.gateway.context import RequestContext

    reset_circuits_for_tests()
    assert circuits_corrupt() is True
    assert get_circuits().allow("deepseek") is False

    d = admit("deepseek", op="chat", tokens_est=10, ctx=RequestContext(consumer="x"))
    assert d.allowed is False
    assert "circuit" in (d.reason or "").lower()

    out = reset_circuits(all_circuits=True)
    assert out.get("ok") is True
    reset_circuits_for_tests()
    assert circuits_corrupt() is False
    assert get_circuits().allow("deepseek") is True


def test_doctor_readiness_auth_corrupt_not_pass(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    monkeypatch.delenv("TOLLGATE_REQUIRE_AUTH", raising=False)
    user = tmp_path / "User"
    user.mkdir(parents=True)
    (user / "consumers.json").write_text("{not-json", encoding="utf-8")
    (user / "Key.txt").write_text("DEEPSEEK_API_KEY=sk-test-not-real\n")

    from tollgate import consumers as c
    from tollgate.doctor import run_doctor

    c.clear_cache()
    report = run_doctor(live=False)
    auth_check = next(
        x
        for x in (report.get("production_readiness") or {}).get("checks") or []
        if x.get("label") == "Authentication"
    )
    assert auth_check.get("ok") is False
    assert "corrupt" in str(auth_check.get("detail") or "").lower()
    assert any(i.get("code") == "consumers_corrupt" for i in (report.get("issues") or []))
