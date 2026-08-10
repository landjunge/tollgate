"""
Keys mini-app configuration — user-editable, provider-based.

Stored at:  <WS>/User/keys_app.json
Override:   TOLLGATE_CONFIG=/path/to.json
"""

from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

from tollgate.paths import user_dir

_LOCK = threading.RLock()
_CACHE: dict[str, Any] | None = None
_CACHE_MTIME: float | None = None

CONFIG_NAME = "keys_app.json"

# ── defaults: almost an app ───────────────────────────────────────────
DEFAULT_CONFIG: dict[str, Any] = {
    "version": 2,
    "prefer_free": True,
    "auto_failover": True,
    "record_usage": True,
    # Hard money guards — Google/Gemini etc. bill silently and fast
    "cost_guard": {
        "enabled": True,
        "max_usd_day_global": 5.0,
        "require_explicit_enable_for_high_risk": True,
        "high_risk_providers": ["google", "gemini", "vertex"],
        "notes": (
            "Google/Gemini/Vertex are complex and easy to overspend. "
            "They stay disabled until you set providers.google.enabled=true "
            "AND tight max_usd_day / max_calls_day."
        ),
    },
    "auto_update": {
        "enabled": True,
        "interval_s": 300,
        "live_probes": False,  # live probes on interval (Brave costs quota if true)
        "refresh_models": True,
    },
    "routing": {
        # first match that is enabled + under limits + ready wins
        # never put google in free_llm by default
        "intents": {
            "llm": ["opencode_zen", "deepseek", "nvidia", "openrouter", "worker"],
            "free_llm": ["opencode_zen", "nvidia", "openrouter"],
            "paid_llm": ["deepseek", "openrouter", "opencode_zen"],
            "search": ["brave"],
            "tts": ["elevenlabs"],
            "media": ["minimax", "elevenlabs"],
        },
        "models": {
            "opencode_zen": "deepseek-v4-flash-free",
            "deepseek": "deepseek-v4-flash",
            "worker": "deepseek-v4-flash",
            "openrouter": "openrouter/free",
            "nvidia": "",
        },
    },
    "providers": {
        "deepseek": {
            "enabled": True,
            "priority": 50,
            "max_calls_day": 2000,
            "max_tokens_day": 2_000_000,
            "max_tokens_call": 32_000,
            "min_interval_ms": 0,
        },
        "worker": {
            "enabled": True,
            "priority": 45,
            "max_calls_day": 4000,
            "max_tokens_day": 4_000_000,
            "max_tokens_call": 32_000,
            "min_interval_ms": 0,
        },
        "opencode_zen": {
            "enabled": True,
            "priority": 100,
            "max_calls_day": 5000,
            "max_tokens_day": 5_000_000,
            "max_tokens_call": 16_000,
            "min_interval_ms": 0,
            "prefer_free_models": True,
        },
        "openrouter": {
            "enabled": True,
            "priority": 40,
            "max_calls_day": 200,
            "max_tokens_day": 500_000,
            "max_tokens_call": 16_000,
            "min_interval_ms": 100,
            "free_only": True,  # respect OPENROUTER_FREE_ONLY + config
        },
        "nvidia": {
            "enabled": True,
            "priority": 70,
            "max_calls_day": 3000,
            "max_tokens_day": 3_000_000,
            "max_tokens_call": 16_000,
            "min_interval_ms": 0,
        },
        "brave": {
            "enabled": True,
            "priority": 90,
            "max_calls_day": 500,
            "max_tokens_day": 0,  # N/A
            "max_tokens_call": 0,
            "min_interval_ms": 1100,  # respect ~1 req/s
        },
        "elevenlabs": {
            "enabled": True,
            "priority": 80,
            "max_calls_day": 200,
            "max_tokens_day": 0,
            "max_chars_day": 5000,  # TTS chars under floor regime
            "max_tokens_call": 0,
            "min_interval_ms": 0,
            "min_remaining": 5000,  # mirrors ELEVENLABS_MIN_REMAINING when set
        },
        "minimax": {
            "enabled": False,  # dead key until recreated
            "priority": 20,
            "max_calls_day": 500,
            "max_tokens_day": 500_000,
            "max_tokens_call": 16_000,
            "min_interval_ms": 0,
        },
        "telegram": {
            "enabled": False,
            "priority": 0,
            "max_calls_day": 0,
            "max_tokens_day": 0,
            "max_tokens_call": 0,
            "min_interval_ms": 0,
        },
        # Google/Gemini — OFF by default; tight caps if you ever enable
        "google": {
            "enabled": False,
            "priority": 5,
            "high_risk": True,
            "max_calls_day": 20,
            "max_tokens_day": 50_000,
            "max_tokens_call": 8_000,
            "max_usd_day": 1.0,
            "min_interval_ms": 500,
            "notes": (
                "Gemini/Vertex can rack up bills fast (multimodal, grounding, long context). "
                "Only enable intentionally. Prefer Zen free / DeepSeek / NVIDIA instead."
            ),
        },
    },
}


def config_path(root: Path | None = None) -> Path:
    for key in ("TOLLGATE_CONFIG", "GNOM_KEYS_CONFIG"):
        env = (os.environ.get(key) or "").strip()
        if env:
            return Path(env).expanduser().resolve()
    return (user_dir(root) / CONFIG_NAME).resolve()


def _deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for k, v in (over or {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def load_config(*, force: bool = False, root: Path | None = None) -> dict[str, Any]:
    """Load config with defaults; auto-create file if missing."""
    global _CACHE, _CACHE_MTIME
    path = config_path(root)
    with _LOCK:
        mtime = path.stat().st_mtime if path.is_file() else None
        if (
            not force
            and _CACHE is not None
            and mtime is not None
            and mtime == _CACHE_MTIME
        ):
            return deepcopy(_CACHE)

        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    raw = {}
            except Exception:  # noqa: BLE001
                raw = {}
            cfg = _deep_merge(DEFAULT_CONFIG, raw)
        else:
            cfg = deepcopy(DEFAULT_CONFIG)
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(cfg, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
            except Exception:  # noqa: BLE001
                pass

        _CACHE = cfg
        _CACHE_MTIME = path.stat().st_mtime if path.is_file() else None
        return deepcopy(cfg)


def save_config(cfg: dict[str, Any], *, root: Path | None = None) -> dict[str, Any]:
    """Write config (merged with defaults for safety)."""
    global _CACHE, _CACHE_MTIME
    path = config_path(root)
    merged = _deep_merge(DEFAULT_CONFIG, cfg if isinstance(cfg, dict) else {})
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)
    with _LOCK:
        _CACHE = merged
        _CACHE_MTIME = path.stat().st_mtime
    return deepcopy(merged)


def patch_config(patch: dict[str, Any], *, root: Path | None = None) -> dict[str, Any]:
    cur = load_config(force=True, root=root)
    return save_config(_deep_merge(cur, patch), root=root)


def provider_cfg(provider_id: str, *, root: Path | None = None) -> dict[str, Any]:
    cfg = load_config(root=root)
    return dict((cfg.get("providers") or {}).get(provider_id) or {})


def is_provider_enabled(provider_id: str, *, root: Path | None = None) -> bool:
    p = provider_cfg(provider_id, root=root)
    if not p:
        return True  # unknown → allow (catalog still gates)
    return bool(p.get("enabled", True))
