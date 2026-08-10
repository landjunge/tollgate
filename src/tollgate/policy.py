"""Spend / route policy — preflight before burning credits."""

from __future__ import annotations

from typing import Any

from tollgate.schema import (
    CAP_FREE_LLM,
    CAP_LLM,
    CAP_SEARCH,
    CAP_TTS,
    PROVIDER_CAPS,
)


def preflight(
    service: Any,
    *,
    intent: str,
    cost: int = 0,
    live: bool = False,
) -> dict[str, Any]:
    """
    intent: llm | free_llm | search | tts | media | any
    Returns allow + recommended providers + blockers.
    """
    intent = (intent or "any").strip().lower()
    inv = service.inventory(live=live)
    cards = inv.get("providers") or []
    by_id = {c["id"]: c for c in cards if isinstance(c, dict)}

    needed_cap = {
        "llm": CAP_LLM,
        "free_llm": CAP_FREE_LLM,
        "search": CAP_SEARCH,
        "tts": CAP_TTS,
        "media": "media",
        "any": None,
    }.get(intent)

    candidates: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []

    for cid, card in by_id.items():
        caps = set(PROVIDER_CAPS.get(cid, ()) or card.get("capabilities") or [])
        if needed_cap and needed_cap not in caps and intent != "any":
            continue
        if card.get("optional") and not card.get("ready"):
            continue
        grade = card.get("grade") or "?"
        if not card.get("ready") or grade in ("F", "D"):
            blockers.append(
                {
                    "id": cid,
                    "reason": card.get("error") or f"grade={grade}",
                    "grade": grade,
                }
            )
            continue

        # Provider-specific spend checks
        if cid == "elevenlabs" and intent in ("tts", "any"):
            b = service.call("elevenlabs", "budget", cost=int(cost or 0))
            if not b.get("allowed"):
                blockers.append(
                    {
                        "id": cid,
                        "reason": b.get("error") or "budget blocked",
                        "grade": "D",
                    }
                )
                continue
            candidates.append(
                {
                    "id": cid,
                    "grade": card.get("grade"),
                    "score": _score(card, b.get("allowed_spend")),
                    "why": f"TTS spend left ≈ {b.get('allowed_spend')}",
                    "metrics": {
                        "allowed_spend": b.get("allowed_spend"),
                        "remaining": b.get("remaining"),
                    },
                }
            )
            continue

        if cid == "brave" and intent in ("search", "any"):
            m = card.get("metrics") or {}
            pr = m.get("period_remaining")
            if pr is not None and int(pr) <= 0:
                blockers.append({"id": cid, "reason": "Brave monthly quota empty", "grade": "D"})
                continue
            candidates.append(
                {
                    "id": cid,
                    "grade": card.get("grade"),
                    "score": _score(card, pr),
                    "why": "web search via Brave",
                    "metrics": m,
                }
            )
            continue

        if intent in ("free_llm",) and CAP_FREE_LLM not in caps:
            continue

        # Prefer Zen free gateway over raw NIM catalog when scores otherwise equal
        prefer = 15.0 if (intent == "free_llm" and cid == "opencode_zen") else 0.0
        if intent == "free_llm" and cid == "nvidia":
            prefer = 5.0
        candidates.append(
            {
                "id": cid,
                "grade": card.get("grade"),
                "score": _score(card, None) + prefer,
                "why": (
                    "Zen free models (deepseek-v4-flash-free, …)"
                    if cid == "opencode_zen" and intent == "free_llm"
                    else f"capability match for {intent}"
                ),
                "metrics": card.get("metrics") or {},
            }
        )

    candidates.sort(key=lambda x: (-float(x.get("score") or 0), str(x.get("id"))))
    best = candidates[0] if candidates else None
    return {
        "ok": True,
        "intent": intent,
        "cost": int(cost or 0),
        "allowed": best is not None,
        "recommended": best,
        "candidates": candidates[:6],
        "blockers": blockers[:12],
        "live": live,
    }


def _score(card: dict[str, Any], headroom: Any) -> float:
    g = {"A": 100, "B": 80, "C": 50, "D": 20, "F": 0, "?": 10}.get(
        str(card.get("grade") or "?"), 10
    )
    bonus = 0.0
    if isinstance(headroom, (int, float)):
        bonus = min(20.0, float(headroom) / 100.0)
    return g + bonus


def recommend_model_route(service: Any, *, prefer_free: bool = True) -> dict[str, Any]:
    """
    Suggest LLM route for agents: Zen free → DeepSeek → NVIDIA → OpenRouter free.
    """
    order = (
        ["opencode_zen", "nvidia", "openrouter", "deepseek"]
        if prefer_free
        else ["deepseek", "opencode_zen", "openrouter", "nvidia"]
    )
    inv = service.inventory(live=False)
    by_id = {c["id"]: c for c in (inv.get("providers") or [])}

    picks = []
    for pid in order:
        c = by_id.get(pid)
        if not c or not c.get("ready"):
            continue
        if c.get("grade") in ("F", "D"):
            continue
        model = None
        if pid == "opencode_zen":
            model = "deepseek-v4-flash-free"
        elif pid == "deepseek":
            model = "deepseek-v4-flash"
        elif pid == "openrouter":
            model = "openrouter/free"
        elif pid == "nvidia":
            model = "(pick from /models)"
        picks.append(
            {
                "provider": pid,
                "grade": c.get("grade"),
                "model": model,
                "base_hint": {
                    "opencode_zen": "https://opencode.ai/zen/v1",
                    "deepseek": "https://api.deepseek.com",
                    "openrouter": "https://openrouter.ai/api/v1",
                    "nvidia": "https://integrate.api.nvidia.com/v1",
                }.get(pid),
            }
        )
    return {
        "ok": True,
        "prefer_free": prefer_free,
        "primary": picks[0] if picks else None,
        "fallbacks": picks[1:4],
        "picks": picks,
    }
