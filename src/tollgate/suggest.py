"""
Config suggestions from ledger patterns — propose only, never auto-apply.

Human must confirm (core promise: no surprise reconfiguration).
"""

from __future__ import annotations

from typing import Any

from tollgate.app_config import load_config
from tollgate.usage_ledger import load_usage


def routing_suggestions(*, root: Any = None) -> dict[str, Any]:
    """
    Compare error rates / usage across providers in today's ledger.
    Suggest priority tweaks when one free path is clearly worse.
    """
    cfg = load_config(root=root)
    usage = load_usage(root=root)
    providers = usage.get("providers") or {}
    suggestions: list[dict[str, Any]] = []

    # free_llm chain order
    chain = list((cfg.get("routing") or {}).get("intents", {}).get("free_llm") or [])
    stats: list[dict[str, Any]] = []
    for pid in chain:
        p = providers.get(pid) or {}
        calls = int(p.get("calls") or 0)
        errors = int(p.get("errors") or 0)
        rate = (errors / calls) if calls else 0.0
        stats.append(
            {
                "provider": pid,
                "calls": calls,
                "errors": errors,
                "error_rate": round(rate, 3),
                "usd": float(p.get("usd") or 0),
            }
        )

    # if two free providers have calls, prefer lower error rate first
    usable = [s for s in stats if s["calls"] >= 5]
    if len(usable) >= 2:
        best = min(usable, key=lambda x: (x["error_rate"], x["usd"]))
        worst = max(usable, key=lambda x: (x["error_rate"], -x["calls"]))
        if (
            worst["provider"] != best["provider"]
            and worst["error_rate"] >= best["error_rate"] + 0.15
            and chain
            and chain[0] == worst["provider"]
        ):
            suggestions.append(
                {
                    "type": "routing_priority",
                    "message": (
                        f"{worst['provider']} leads free_llm but error_rate="
                        f"{worst['error_rate']:.0%} vs {best['provider']} "
                        f"{best['error_rate']:.0%} — consider swapping priority"
                    ),
                    "propose": {
                        "routing": {
                            "intents": {
                                "free_llm": [best["provider"]]
                                + [p for p in chain if p != best["provider"]]
                            }
                        }
                    },
                    "auto_apply": False,
                }
            )

    # spend concentration
    totals_usd = float((usage.get("totals") or {}).get("usd") or 0)
    if totals_usd > 0:
        for pid, p in providers.items():
            if not isinstance(p, dict):
                continue
            u = float(p.get("usd") or 0)
            if u >= totals_usd * 0.7 and u >= 0.5:
                suggestions.append(
                    {
                        "type": "spend_concentration",
                        "message": (
                            f"{pid} is {u / totals_usd:.0%} of today's $ spend "
                            f"(${u:.3f}) — tighten max_usd_day or prefer free_llm"
                        ),
                        "propose": {
                            "providers": {pid: {"max_usd_day": max(0.5, round(u, 2))}}
                        },
                        "auto_apply": False,
                    }
                )

    return {
        "ok": True,
        "day": usage.get("day"),
        "stats": stats,
        "suggestions": suggestions,
        "note": "Proposals only — never auto-applied. Review then patch keys_app.json.",
    }
