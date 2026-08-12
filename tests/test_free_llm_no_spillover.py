"""P0 product rule: free_llm never silently routes to paid-only providers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from tollgate.router import route
from tollgate.schema import PROVIDER_CAPS


def test_deepseek_is_paid_only_not_free_capable():
    assert "free_llm" not in PROVIDER_CAPS.get("deepseek", ())
    assert "paid_llm" in PROVIDER_CAPS.get("deepseek", ())


def test_free_llm_does_not_spill_to_paid_when_free_unavailable(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)

    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["routing"] = dict(cfg.get("routing") or {})
    # free_llm chain intentionally includes paid-only deepseek (legacy configs)
    cfg["routing"]["intents"] = {
        "free_llm": ["opencode_zen", "deepseek"],
        "llm": ["opencode_zen", "deepseek"],
    }
    cfg["prefer_free"] = True
    save_config(cfg)

    svc = MagicMock()
    # Free provider not ready; paid-only deepseek is ready — must NOT win free_llm
    svc.inventory.return_value = {
        "providers": [
            {"id": "opencode_zen", "ready": False, "grade": "F", "error": "no key"},
            {"id": "deepseek", "ready": True, "grade": "A"},
        ]
    }

    with patch("tollgate.router.admit") as ad:
        ad.return_value = MagicMock(
            allowed=True,
            soft_degrade=False,
            limits={},
            as_dict=lambda: {"allowed": True},
        )
        r = route(svc, "free_llm", prefer_free=True)

    assert r["ok"] is False
    assert r.get("free_only") is True
    assert r.get("route") is None
    assert "no paid spillover" in (r.get("error") or "").lower() or "no free provider" in (
        r.get("error") or ""
    ).lower()
    # deepseek must appear as excluded, never as winner
    tried_pids = [t.get("provider") for t in (r.get("tried") or [])]
    assert "deepseek" in tried_pids
    skips = {
        t.get("provider"): t.get("skip")
        for t in (r.get("tried") or [])
        if t.get("skip")
    }
    assert "paid" in (skips.get("deepseek") or "").lower() or "spillover" in (
        skips.get("deepseek") or ""
    ).lower()


def test_free_llm_empty_free_chain_stops(monkeypatch, tmp_path):
    """Config only lists paid-only providers under free_llm → hard stop."""
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)

    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["routing"] = dict(cfg.get("routing") or {})
    cfg["routing"]["intents"] = {"free_llm": ["deepseek", "google"]}
    save_config(cfg)

    svc = MagicMock()
    svc.inventory.return_value = {
        "providers": [
            {"id": "deepseek", "ready": True, "grade": "A"},
            {"id": "google", "ready": True, "grade": "A"},
        ]
    }

    with patch("tollgate.router.admit") as ad:
        ad.return_value = MagicMock(
            allowed=True,
            soft_degrade=False,
            limits={},
            as_dict=lambda: {"allowed": True},
        )
        r = route(svc, "free_llm")

    assert r["ok"] is False
    assert r.get("route") is None
    assert "spillover" in (r.get("error") or "").lower() or "free provider" in (
        r.get("error") or ""
    ).lower()


def test_free_llm_uses_free_capable_when_ready(monkeypatch, tmp_path):
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)

    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["routing"] = dict(cfg.get("routing") or {})
    cfg["routing"]["intents"] = {"free_llm": ["deepseek", "opencode_zen"]}
    cfg["routing"]["health_aware"] = False
    save_config(cfg)

    svc = MagicMock()
    svc.inventory.return_value = {
        "providers": [
            {"id": "deepseek", "ready": True, "grade": "A"},
            {"id": "opencode_zen", "ready": True, "grade": "B"},
        ]
    }

    with patch("tollgate.router.admit") as ad:
        ad.return_value = MagicMock(
            allowed=True,
            soft_degrade=False,
            limits={},
            as_dict=lambda: {"allowed": True},
        )
        r = route(svc, "free_llm", prefer_free=True)

    assert r["ok"] is True
    assert r["route"]["provider"] == "opencode_zen"
    assert r.get("free_only") is True


def test_llm_intent_may_still_use_paid_as_fallback(monkeypatch, tmp_path):
    """intent=llm is not free-only — paid spillover after free is allowed."""
    monkeypatch.setenv("TOLLGATE_HOME", str(tmp_path))
    (tmp_path / "User").mkdir(parents=True)

    from tollgate.app_config import load_config, save_config

    cfg = load_config(force=True)
    cfg["routing"] = dict(cfg.get("routing") or {})
    cfg["routing"]["intents"] = {"llm": ["opencode_zen", "deepseek"]}
    cfg["routing"]["health_aware"] = False
    cfg["prefer_free"] = True
    save_config(cfg)

    svc = MagicMock()
    svc.inventory.return_value = {
        "providers": [
            {"id": "opencode_zen", "ready": False, "grade": "F", "error": "no key"},
            {"id": "deepseek", "ready": True, "grade": "A"},
        ]
    }

    with patch("tollgate.router.admit") as ad:
        ad.return_value = MagicMock(
            allowed=True,
            soft_degrade=False,
            limits={},
            as_dict=lambda: {"allowed": True},
        )
        r = route(svc, "llm", prefer_free=True)

    assert r["ok"] is True
    assert r["route"]["provider"] == "deepseek"
    assert r.get("free_only") is not True
