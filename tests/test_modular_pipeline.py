"""Phase 1–7 modular monolith facades — no public API break."""

from __future__ import annotations


def test_decision_deny_shape():
    from tollgate.gateway.decision import Decision
    from tollgate.gateway.errors import ErrorClass

    d = Decision.deny(
        "agent protection: max_tokens",
        code=ErrorClass.BUDGET_HARD,
        provider="deepseek",
        op="chat",
        protection="max_tokens_request",
    )
    out = d.as_dict()
    assert out["ok"] is False
    assert out["error_class"] == "BUDGET_HARD"
    assert "max_tokens" in out["error"]
    assert out["protection"] == "max_tokens_request"


def test_package_deny_has_blocked_card(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.protect import package_deny

    out = package_deny(
        provider="deepseek",
        op="chat",
        reason="agent protection: max_tokens_request",
        code="BUDGET_HARD",
        consumer="agent-x",
        protection="max_tokens_request",
        tokens_est=99_000,
        audit=False,
        alert=False,
    )
    assert out["ok"] is False
    assert out["error_class"] == "BUDGET_HARD"
    assert out["protection"] == "max_tokens_request"
    assert isinstance(out.get("blocked"), dict)
    assert out["blocked"].get("headline") == "REQUEST BLOCKED"


def test_package_deny_from_admit_parity(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.gateway.admit import AdmitDecision
    from tollgate.gateway.errors import ErrorClass
    from tollgate.protect import package_deny_from_admit

    ad = AdmitDecision(
        allowed=False,
        code=ErrorClass.BUDGET_HARD,
        reason="max_tokens_request exceeded",
        limits={"protection": "max_tokens_request", "max_tokens_request": 1000},
    )
    out = package_deny_from_admit(
        ad,
        provider="deepseek",
        op="chat",
        consumer="c1",
        tokens_est=5000,
        extra_audit={"stream": True},
    )
    assert out["ok"] is False
    assert out["protection"] == "max_tokens_request"
    assert out.get("blocked")


def test_axis_facade_packages():
    from tollgate import accounting, audit, identity, protect, prove, route

    assert callable(protect.package_deny)
    assert callable(protect.record_rates)
    assert callable(prove.check_provider_available)
    assert callable(route.select_route)
    assert callable(identity.normalize_consumer)
    assert callable(accounting.try_reserve_day_call)
    assert callable(audit.append_audit)


def test_no_protect_imports_route():
    """Architect rule: Protect must not import Route (or router/failover)."""
    import ast
    from pathlib import Path

    banned = ("tollgate.route", "tollgate.router", "tollgate.failover")
    root = Path(__file__).resolve().parents[1] / "src" / "tollgate" / "protect"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(node.module.startswith(b) for b in banned), path
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(alias.name.startswith(b) for b in banned), path


def test_route_facade_exposes_circuits_corrupt():
    from tollgate.route import circuits_corrupt, get_circuits, reset_circuits

    assert callable(circuits_corrupt)
    assert callable(get_circuits)
    assert callable(reset_circuits)


def test_decision_from_admit(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.gateway.admit import AdmitDecision
    from tollgate.gateway.decision import from_admit_decision
    from tollgate.gateway.errors import ErrorClass

    ad = AdmitDecision(
        allowed=False,
        code=ErrorClass.POLICY_DENY,
        reason="frozen",
        limits={"protection": "freeze"},
    )
    d = from_admit_decision(ad, provider="deepseek", op="chat")
    assert d.allowed is False
    assert d.protection == "freeze"


def test_prove_availability_ok_default(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from tollgate.prove.availability import check_provider_available

    av = check_provider_available("deepseek")
    assert av.available is True


def test_prove_availability_fail_closed_on_error(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)
    from unittest.mock import patch

    from tollgate.prove.availability import check_provider_available

    with patch(
        "tollgate.chaos.is_provider_unavailable",
        side_effect=RuntimeError("boom"),
    ):
        av = check_provider_available("deepseek")
    assert av.available is False
    assert av.subsystem_error is True


def test_protect_facade_imports():
    from tollgate.protect import admit, evaluate_protect, record_rates

    assert callable(admit)
    assert callable(evaluate_protect)
    assert callable(record_rates)


def test_route_facade_imports():
    from tollgate.route import build_candidates, get_circuits, select_route

    assert callable(build_candidates)
    assert callable(get_circuits)
    assert callable(select_route)


def test_stream_uses_entry_protect_stages():
    """M6b: stream must not keep a private prove/admit/rates copy."""
    import inspect

    from tollgate import chat_stream
    from tollgate.gateway import entry

    src = inspect.getsource(chat_stream.start_chat_stream)
    assert "_stage_prove_availability" in src
    assert "_stage_protect_admit" in src
    assert "_stage_protect_rates" in src
    assert "check_provider_available" not in src
    assert callable(entry._stage_prove_availability)
    assert callable(entry._stage_protect_admit)
    assert callable(entry._stage_protect_rates)


def test_gateway_call_still_public():
    from tollgate import gateway_call
    from tollgate.gateway import Decision, gateway_call as gc2

    assert gateway_call is gc2
    assert Decision is not None
