"""USD cost estimates + high-risk provider guards (Google etc.)."""

from __future__ import annotations

from typing import Any

from tollgate.distill.loader import load_distill
from tollgate.app_config import load_config, provider_cfg
from tollgate.usage_ledger import load_usage, provider_usage

# Fallback rough USD per 1M tokens (input/output) when distill lacks rates
_FALLBACK_RATES: dict[str, tuple[float, float]] = {
    "google": (0.50, 1.50),
    "openrouter": (0.20, 0.60),
    "deepseek": (0.14, 0.28),
    "worker": (0.14, 0.28),
    "opencode_zen": (0.0, 0.0),  # free default path
    "nvidia": (0.0, 0.0),
    "minimax": (0.30, 1.20),
    "brave": (0.0, 0.0),
    "elevenlabs": (0.0, 0.0),  # chars not tokens
    "telegram": (0.0, 0.0),
}


def is_high_risk(provider_id: str) -> bool:
    d = load_distill(provider_id)
    if d.get("high_risk"):
        return True
    cfg = load_config()
    guard = cfg.get("cost_guard") or {}
    risky = guard.get("high_risk_providers") or ["google", "gemini", "vertex"]
    return (provider_id or "").strip().lower() in {str(x).lower() for x in risky}


def estimate_usd(
    provider_id: str,
    *,
    tokens_in: int = 0,
    tokens_out: int = 0,
) -> float:
    """Rough USD estimate for budgeting — not a bill."""
    tin = max(0, int(tokens_in or 0))
    tout = max(0, int(tokens_out or 0))
    d = load_distill(provider_id)
    rates = d.get("usd_estimate_per_1m_tokens") or {}
    if isinstance(rates, dict) and ("input" in rates or "output" in rates):
        rin = float(rates.get("input") or 0)
        rout = float(rates.get("output") or 0)
    else:
        rin, rout = _FALLBACK_RATES.get(
            (provider_id or "").strip().lower(), (0.25, 0.75)
        )
    return (tin / 1_000_000.0) * rin + (tout / 1_000_000.0) * rout


def usd_used_today(provider_id: str | None = None) -> float:
    if provider_id:
        p = provider_usage(provider_id)
        return float(p.get("usd") or 0.0)
    data = load_usage()
    tot = data.get("totals") or {}
    return float(tot.get("usd") or 0.0)


def check_cost_guard(
    provider_id: str,
    *,
    tokens_est: int = 0,
    usd_est: float | None = None,
) -> dict[str, Any]:
    """
    Block high-risk / over-budget providers.

    - cost_guard.require_explicit_enable_for_high_risk + disabled → block
    - max_usd_day (provider or global)
    """
    pid = (provider_id or "").strip().lower()
    cfg = load_config()
    guard = cfg.get("cost_guard") or {}
    pcfg = provider_cfg(pid)

    # High-risk must be explicitly enabled
    if bool(guard.get("enabled", True)) and bool(
        guard.get("require_explicit_enable_for_high_risk", True)
    ):
        if is_high_risk(pid) and not bool(pcfg.get("enabled", False)):
            return {
                "allowed": False,
                "reason": (
                    f"{pid} is HIGH RISK (can bill hard — e.g. Google/Gemini). "
                    "Kept disabled. Enable only in keys_app.json with tight max_usd_day."
                ),
                "high_risk": True,
                "remaining_usd": 0.0,
            }

    used = usd_used_today(pid)
    used_global = usd_used_today(None)
    est = float(usd_est) if usd_est is not None else estimate_usd(
        pid, tokens_in=int(tokens_est or 0) // 2, tokens_out=int(tokens_est or 0) // 2
    )

    max_p = float(pcfg.get("max_usd_day") or 0)
    max_g = float(guard.get("max_usd_day_global") or 0)

    if max_p > 0 and (used + est) > max_p:
        return {
            "allowed": False,
            "reason": f"max_usd_day {pid}: {used:.4f}+{est:.4f} > {max_p}",
            "high_risk": is_high_risk(pid),
            "remaining_usd": max(0.0, max_p - used),
            "used_usd": used,
        }
    if max_g > 0 and (used_global + est) > max_g:
        return {
            "allowed": False,
            "reason": f"global max_usd_day: {used_global:.4f}+{est:.4f} > {max_g}",
            "high_risk": is_high_risk(pid),
            "remaining_usd": max(0.0, max_g - used_global),
            "used_usd": used_global,
        }

    rem_p = (max_p - used) if max_p > 0 else None
    rem_g = (max_g - used_global) if max_g > 0 else None
    remaining = None
    if rem_p is not None and rem_g is not None:
        remaining = min(rem_p, rem_g)
    elif rem_p is not None:
        remaining = rem_p
    elif rem_g is not None:
        remaining = rem_g

    return {
        "allowed": True,
        "reason": None,
        "high_risk": is_high_risk(pid),
        "remaining_usd": remaining,
        "used_usd": used,
        "est_usd": est,
        "max_usd_day": max_p or None,
        "max_usd_day_global": max_g or None,
    }
