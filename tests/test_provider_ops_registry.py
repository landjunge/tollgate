"""M9 provider_ops registry — KeysService does not own provider maps."""

from __future__ import annotations


def test_registry_lists_core_providers():
    from tollgate.provider_ops import get_ops, list_provider_ids

    ids = list_provider_ids()
    for need in ("deepseek", "opencode_zen", "brave", "openrouter"):
        assert need in ids
    assert "chat" in get_ops("deepseek")
    assert "search" in get_ops("brave")


def test_keys_service_uses_registry_ops():
    from tollgate.provider_ops import get_ops
    from tollgate.service import KeysService

    # same op set KeysService would call
    assert "status" in get_ops("nvidia")
    ks = KeysService()
    # research lists ops from registry path
    r = ks.research("nvidia")
    assert r.get("ok") is True
    assert "status" in (r.get("ops") or [])


def test_execute_op_unknown():
    from tollgate.provider_ops import execute_op
    import pytest

    with pytest.raises(KeyError):
        execute_op("no_such_provider", "chat")
