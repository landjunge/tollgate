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
    # Emergency kill switch — deny all billable traffic when frozen
    "admission": {
        "frozen": False,
        "frozen_reason": "",
        "frozen_at": None,
        "frozen_by": "",
        "allow_system_when_frozen": True,
        "notes": (
            "tollgate freeze / unfreeze. Env TOLLGATE_FROZEN=1 overrides. "
            "System probes still pass if allow_system_when_frozen=true."
        ),
    },
    # Prove pillar — continuous reliability targets (DR / chaos)
    "reliability": {
        "availability_target": 99.9,
        "max_failover_time_s": 5.0,
        "required_fallbacks": 2,
        "gradual_recovery_s": 60.0,
        "notes": (
            "availability_target is aspirational for reporting. "
            "required_fallbacks = min enabled providers per LLM intent. "
            "max_failover_time_s checked against last chaos test recovery_time. "
            "gradual_recovery_s > 0 ramps traffic back after chaos stop (0 = immediate)."
        ),
    },
    # Hard money guards — Google/Gemini etc. bill silently and fast
    "cost_guard": {
        "enabled": True,
        "max_usd_day_global": 5.0,
        "require_explicit_enable_for_high_risk": True,
        # Any id listed here (or distill high_risk=true) needs explicit enable
        "high_risk_providers": ["google", "gemini", "vertex"],
        # Soft pressure: fraction of day budget used → warn / webhook (not deny)
        "soft_warn_ratio": 0.8,
        "soft_warn_remaining_usd": 0.5,
        "anomaly_burn_factor": 5.0,
        # Optional webhook (Telegram bot URL, n8n, Discord, …) on soft/hard events
        "alert_webhook_url": "",
        "notes": (
            "high_risk_providers are OFF until providers.<id>.enabled=true "
            "with tight max_usd_day. Add azure_openai / anthropic / etc. as needed. "
            "anomaly_burn_factor: soft_warn if spend ≫ linear day pace (no auto config change)."
        ),
    },
    # Circuit breaker defaults (per provider|model|key_ref)
    "circuits": {
        "failure_threshold": 5,
        "cooldown_s": 30.0,
        "hard_cooldown_s": 300.0,
        "half_open_successes_needed": 1,
        # Multiplicative jitter on OPEN→HALF_OPEN wait: cooldown * [min, max]
        "jitter_min": 0.8,
        "jitter_max": 1.2,
        "notes": (
            "jitter_min/max spread canary wake-ups to avoid thundering herd. "
            "hard_cooldown_s elevates cooldown_s on AUTH_DEAD (and other hard "
            "failures); the elevated value is persisted on the circuit row. "
            "Omit this whole block on old installs — defaults apply."
        ),
    },
    # Per-consumer day envelopes + agent protection.
    # Safe _default: Protect is on out of the box (set 0 = unlimited on that dim).
    # Named lanes (n8n / gnom) override via tollgate consumer-budget.
    "consumer_envelopes": {
        "_default": {
            "max_calls_day": 2000,
            "max_tokens_day": 2_000_000,
            "max_usd_day": 5.0,
            "max_usd_request": 0.5,
            "max_usd_hour": 2.0,
            "max_requests_minute": 60,
            "max_tokens_request": 50_000,
            "max_tool_calls": 25,
        },
        # Examples:
        # "n8n": {
        #   "max_usd_day": 0.5, "max_requests_minute": 30, "max_usd_request": 0.25,
        #   "allowed_providers": ["opencode_zen", "brave"],
        #   "allowed_intents": ["free_llm", "search"],
        #   "blocked_providers": ["google"]
        # },
        # "coding-agent": {
        #   "max_usd_day": 20, "max_usd_hour": 5, "max_usd_request": 0.5,
        #   "max_requests_minute": 30, "max_tokens_request": 20000, "max_tool_calls": 15
        # },
    },
    "auto_update": {
        "enabled": True,
        "interval_s": 300,
        "live_probes": False,  # live probes on interval (Brave costs quota if true)
        "refresh_models": True,
    },
    # Operational response cache only — never agent memory / interactive chat default
    "response_cache": {
        "enabled": True,
        "ttl_s": 300,
        "max_entries": 256,
        "ops": ["search", "status", "quota", "models", "credits", "research"],
        "request_classes": ["free", "batch", "system"],
        "allow_interactive": False,
        "include_consumer_in_key": True,
        "notes": (
            "Caches idempotent free/batch probes and search. "
            "Not for interactive chat. Never high-risk providers. "
            "Key = provider|op|args|consumer. No chat transcripts in ledger."
        ),
    },
    "routing": {
        # Admitted candidates are ranked when health_aware=true
        "health_aware": True,
        # balanced | reliability | cost_optimized
        "strategy": "balanced",
        # never put google in free_llm by default
        "intents": {
            "llm": ["opencode_zen", "deepseek", "nvidia", "openrouter", "worker"],
            # deepseek after zen — most desks have DEEPSEEK_API_KEY; nvidia/openrouter often missing
            "free_llm": ["opencode_zen", "deepseek", "openrouter", "nvidia"],
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
        "notes": (
            "health_aware reorders admitted providers by reliability/latency/cost. "
            "strategy=cost_optimized weights day spend; reliability weights health score."
        ),
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
            parse_err = ""
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    raise ValueError("keys_app.json is not an object")
            except Exception as e:  # noqa: BLE001
                from tollgate.soft_fail import soft_fail

                parse_err = str(e)[:200]
                soft_fail("config_parse", e)
                raw = {}
            cfg = _deep_merge(DEFAULT_CONFIG, raw)
            if parse_err:
                # Do not lift freeze / custom envelopes by treating junk as empty.
                cfg["_corrupt"] = True
                cfg["_corrupt_reason"] = f"json_parse: {parse_err}"
        else:
            cfg = deepcopy(DEFAULT_CONFIG)
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(cfg, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
            except Exception as e:  # noqa: BLE001
                from tollgate.soft_fail import soft_fail

                soft_fail("config_write_default", e)

        # Soft validate (warnings only unless TOLLGATE_STRICT_CONFIG=1)
        try:
            from tollgate.config_validate import assert_config_or_raise

            strict = (os.environ.get("TOLLGATE_STRICT_CONFIG") or "").strip().lower() in (
                "1",
                "true",
                "yes",
            )
            assert_config_or_raise(cfg, strict=strict)
        except ValueError:
            raise
        except Exception as e:  # noqa: BLE001
            from tollgate.soft_fail import soft_fail

            soft_fail("config_validate", e)

        _CACHE = cfg
        _CACHE_MTIME = path.stat().st_mtime if path.is_file() else None
        return deepcopy(cfg)


def config_corrupt(*, root: Path | None = None) -> bool:
    """True when keys_app.json exists but could not be parsed."""
    return bool(load_config(root=root).get("_corrupt"))


def save_config(
    cfg: dict[str, Any],
    *,
    root: Path | None = None,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Write config (merged with defaults for safety).

    When ``validate=True`` (default), runs the same schema/semantic checks as
    process start so a live PATCH cannot leave a broken keys_app.json.
    """
    global _CACHE, _CACHE_MTIME
    path = config_path(root)
    incoming = cfg if isinstance(cfg, dict) else {}
    incoming = {
        k: v
        for k, v in incoming.items()
        if k not in ("_corrupt", "_corrupt_reason")
    }
    merged = _deep_merge(DEFAULT_CONFIG, incoming)
    if validate:
        from tollgate.config_validate import validate_config_dict

        data, errs = validate_config_dict(merged)
        if errs:
            raise ValueError("keys_app.json invalid:\n- " + "\n- ".join(errs))
        if data is not None:
            # Keep defaults filled by validator for stability
            merged = _deep_merge(DEFAULT_CONFIG, data)
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
    return save_config(_deep_merge(cur, patch), root=root, validate=True)


def provider_cfg(provider_id: str, *, root: Path | None = None) -> dict[str, Any]:
    cfg = load_config(root=root)
    return dict((cfg.get("providers") or {}).get(provider_id) or {})


def is_provider_enabled(provider_id: str, *, root: Path | None = None) -> bool:
    p = provider_cfg(provider_id, root=root)
    if not p:
        return True  # unknown → allow (catalog still gates)
    return bool(p.get("enabled", True))
