"""
Provider op registry (M9) — KeysService must not own every provider.

Lookup:
  get_ops(pid)[op](**kwargs)
  get_status(pid)(**kwargs)

Adding provider 15: register here (or later: ProviderAdapter class).
Logic stays in deepseek/brave/… modules.
"""

from __future__ import annotations

from typing import Any, Callable

from tollgate import brave as brave_mod
from tollgate import deepseek as deepseek_mod
from tollgate import elevenlabs as el_mod
from tollgate import google as google_mod
from tollgate import minimax as minimax_mod
from tollgate import nvidia as nvidia_mod
from tollgate import opencode_zen as zen_mod
from tollgate import openrouter as openrouter_mod
from tollgate import providers as generic
from tollgate.research_notes import research_for

STATUS: dict[str, Callable[..., dict[str, Any]]] = {
    "deepseek": lambda **kw: deepseek_mod.status(worker=False, **kw),
    "worker": lambda **kw: deepseek_mod.status(worker=True, **kw),
    "brave": brave_mod.status,
    "elevenlabs": el_mod.status,
    "openrouter": openrouter_mod.status,
    "nvidia": nvidia_mod.status,
    "minimax": minimax_mod.status,
    "opencode_zen": zen_mod.status,
    "telegram": generic.telegram_status,
    "google": google_mod.status,
}

OPS: dict[str, dict[str, Callable[..., Any]]] = {
    "elevenlabs": {
        "status": lambda **kw: el_mod.status(**kw),
        "budget": lambda cost=0, **_kw: el_mod.check_budget(cost=int(cost or 0)),
        "subscription": lambda force=False, **_kw: el_mod.fetch_subscription(
            force=bool(force)
        ),
        "ensure_budget": lambda cost=0, **_kw: el_mod.ensure_budget(cost=int(cost or 0)),
        "research": lambda **_kw: research_for("elevenlabs"),
    },
    "brave": {
        "status": lambda **kw: brave_mod.status(**kw),
        "search": lambda query="", count=5, country="DE", search_lang="de", **_kw: brave_mod.search(
            str(query),
            count=int(count or 5),
            country=str(country or "DE"),
            search_lang=str(search_lang or "de"),
        ),
        "quota": lambda force=False, **_kw: brave_mod.quota(force=bool(force)),
        "research": lambda **_kw: research_for("brave"),
    },
    "deepseek": {
        "status": lambda **kw: deepseek_mod.status(worker=False, **kw),
        "models": lambda **_kw: deepseek_mod.list_models(worker=False),
        "chat": lambda messages="hi", model=None, max_tokens=1024, temperature=0.7, **kw: deepseek_mod.chat(
            messages,
            model=model,
            max_tokens=int(max_tokens or 1024),
            temperature=float(temperature or 0.7),
            worker=False,
            **kw,
        ),
        "research": lambda **_kw: research_for("deepseek"),
    },
    "worker": {
        "status": lambda **kw: deepseek_mod.status(worker=True, **kw),
        "models": lambda **_kw: deepseek_mod.list_models(worker=True),
        "chat": lambda messages="hi", model=None, max_tokens=1024, temperature=0.7, **kw: deepseek_mod.chat(
            messages,
            model=model,
            max_tokens=int(max_tokens or 1024),
            temperature=float(temperature or 0.7),
            worker=True,
            **kw,
        ),
        "research": lambda **_kw: research_for("worker"),
    },
    "openrouter": {
        "status": lambda **kw: openrouter_mod.status(**kw),
        "credits": lambda **_kw: openrouter_mod.credits(),
        "models": lambda **_kw: openrouter_mod.models(),
        "chat": lambda messages="hi", model="openrouter/free", max_tokens=1024, temperature=0.7, **kw: openrouter_mod.chat(
            messages,
            model=str(model or "openrouter/free"),
            max_tokens=int(max_tokens or 1024),
            temperature=float(temperature or 0.7),
            **kw,
        ),
        "research": lambda **_kw: research_for("openrouter"),
    },
    "nvidia": {
        "status": lambda **kw: nvidia_mod.status(**kw),
        "models": lambda **_kw: nvidia_mod.list_models(),
        "research": lambda **_kw: research_for("nvidia"),
    },
    "minimax": {
        "status": lambda **kw: minimax_mod.status(**kw),
        "probe": lambda **_kw: minimax_mod.probe_key(),
        "research": lambda **_kw: research_for("minimax"),
    },
    "opencode_zen": {
        "status": lambda **kw: zen_mod.status(**kw),
        "models": lambda **_kw: zen_mod.list_models(),
        "chat": lambda message="hi", messages=None, model="deepseek-v4-flash-free", max_tokens=1024, temperature=0.7, **_kw: zen_mod.chat(
            message if messages is None else messages,
            model=str(model or "deepseek-v4-flash-free"),
            max_tokens=int(max_tokens or 1024),
            messages=messages,
            temperature=float(temperature or 0.7),
        ),
        "research": lambda **_kw: research_for("opencode_zen"),
    },
    "telegram": {
        "status": lambda **kw: generic.telegram_status(**kw),
        "research": lambda **_kw: research_for("telegram"),
    },
    "google": {
        "status": lambda **kw: google_mod.status(**kw),
        "research": lambda **_kw: research_for("google"),
    },
}

def list_provider_ids() -> list[str]:
    return sorted(OPS.keys())


def get_ops(provider_id: str) -> dict[str, Callable[..., Any]]:
    pid = (provider_id or "").strip().lower()
    return dict(OPS.get(pid) or {})


def get_status(provider_id: str) -> Callable[..., dict[str, Any]] | None:
    pid = (provider_id or "").strip().lower()
    return STATUS.get(pid)


def has_provider(provider_id: str) -> bool:
    pid = (provider_id or "").strip().lower()
    return pid in OPS or pid in STATUS


def available_ops(provider_id: str) -> list[str]:
    return sorted(get_ops(provider_id).keys())


def execute_op(provider_id: str, op: str, **kwargs: Any) -> Any:
    """Run a registered provider op. Raises KeyError if unknown."""
    pid = (provider_id or "").strip().lower()
    oname = (op or "status").strip().lower()
    ops = get_ops(pid)
    if not ops:
        raise KeyError(f"unknown provider: {provider_id}")
    fn = ops.get(oname)
    if fn is None:
        raise KeyError(f"unknown op {op!r} for {pid}; available={list(ops.keys())}")
    return fn(**kwargs)
