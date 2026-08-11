"""Load provider distillates — single source of truth for keys functions."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def distill_dir() -> Path:
    return _DIR


@lru_cache(maxsize=32)
def load_distill(provider_id: str) -> dict[str, Any]:
    """Load one provider distill JSON (empty dict if missing)."""
    pid = (provider_id or "").strip().lower()
    if not pid or pid in (".", "..") or "/" in pid or "\\" in pid:
        return {}
    path = _DIR / f"{pid}.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        data.setdefault("schema_version", 1)
        return data
    except Exception:  # noqa: BLE001
        return {}


def list_distill_ids() -> list[str]:
    return sorted(p.stem for p in _DIR.glob("*.json") if p.name != "schema.json")


def all_distills() -> dict[str, dict[str, Any]]:
    return {pid: load_distill(pid) for pid in list_distill_ids()}


def ops_for(provider_id: str) -> list[dict[str, Any]]:
    d = load_distill(provider_id)
    ops = d.get("ops") or []
    return [o for o in ops if isinstance(o, dict)]


def research_view(provider_id: str) -> dict[str, Any]:
    """
    Shape compatible with legacy research_notes / MCP research op.

    Prefer distill; fall back to empty.
    """
    d = load_distill(provider_id)
    if not d:
        return {}
    auth = d.get("auth") or {}
    auth_s = auth.get("summary") or ""
    if not auth_s and auth.get("header"):
        auth_s = f"{auth.get('header')}: <{','.join(auth.get('env') or [])}>"
    limits = d.get("limits") or {}
    hub = d.get("hub") or {}
    return {
        "researched_at": d.get("distilled_at"),
        "docs": (d.get("sources") or [None])[0],
        "sources": d.get("sources") or [],
        "base_url": (d.get("base_urls") or {}).get("default"),
        "base_urls": d.get("base_urls") or {},
        "auth": auth_s or auth,
        "auth_detail": auth,
        "key_prefix": auth.get("key_prefix"),
        "probe": hub.get("probe") or d.get("probe"),
        "probe_kind": hub.get("probe_kind") or limits.get("probe_kind"),
        "probe_cost": hub.get("probe_cost"),
        "endpoints": d.get("endpoints") or [],
        "models_known": d.get("models") or d.get("models_known") or [],
        "free_models": d.get("free_models") or [],
        "limits": limits,
        "errors": d.get("errors") or {},
        "special_ops": [o.get("name") for o in ops_for(provider_id) if o.get("name")],
        "ops": ops_for(provider_id),
        "gotchas": d.get("gotchas") or [],
        "headers_out": d.get("headers_out") or [],
        "hub": hub,
        "env_names": auth.get("env") or [],
        "env_chain": auth.get("env_chain") or auth.get("env") or [],
        "openai_compatible": bool(d.get("openai_compatible")),
        "title": d.get("title"),
        "id": d.get("id") or provider_id,
    }


def clear_cache() -> None:
    load_distill.cache_clear()
    all_distills.cache_clear() if hasattr(all_distills, "cache_clear") else None
    list_distill_ids.cache_clear()
