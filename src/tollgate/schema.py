"""Unified health schema — every provider status normalizes here."""

from __future__ import annotations

from typing import Any, Literal

Grade = Literal["A", "B", "C", "D", "F", "?"]

# Capability tags for routing / preflight
CAP_LLM = "llm"
CAP_SEARCH = "search"
CAP_TTS = "tts"
CAP_MEDIA = "media"
CAP_OPTIONAL = "optional"
CAP_FREE_LLM = "free_llm"
CAP_PAID_LLM = "paid_llm"


PROVIDER_CAPS: dict[str, tuple[str, ...]] = {
    "deepseek": (CAP_LLM, CAP_PAID_LLM),
    "worker": (CAP_LLM, CAP_PAID_LLM),
    "brave": (CAP_SEARCH,),
    "elevenlabs": (CAP_TTS,),
    "openrouter": (CAP_LLM, CAP_FREE_LLM, CAP_PAID_LLM),
    "nvidia": (CAP_LLM, CAP_FREE_LLM),
    "minimax": (CAP_LLM, CAP_MEDIA, CAP_TTS),
    "opencode_zen": (CAP_LLM, CAP_FREE_LLM, CAP_PAID_LLM),
    "telegram": (CAP_OPTIONAL,),
    "google": (CAP_LLM, CAP_PAID_LLM),  # never free_llm by default
}


def grade_provider(
    *,
    ready: bool,
    live: bool,
    error: str | None,
    detail: dict[str, Any] | None,
    provider_id: str,
) -> Grade:
    """
    A = live-verified + healthy headroom
    B = ready, minor limits or presence-ok
    C = ready but constrained (low credits / floor near)
    D = present but failing / unverified-risky
    F = missing or dead
    ? = unknown
    """
    d = detail or {}
    if not ready:
        if error and "unverified" in str(error).lower():
            return "D"
        if error and any(x in str(error).lower() for x in ("missing", "not set", "invalid")):
            return "F"
        return "F" if error else "?"

    # Headroom signals
    spend = d.get("allowed_spend")
    lim_rem = d.get("limit_remaining")
    period_rem = d.get("period_remaining")
    chat_probe = d.get("chat_probe") or {}

    if provider_id == "elevenlabs":
        if isinstance(spend, (int, float)) and spend <= 0:
            return "D"
        if isinstance(spend, (int, float)) and spend < 500:
            return "C"
        return "A" if live else "B"

    if provider_id == "openrouter":
        if lim_rem is not None and float(lim_rem) <= 0:
            return "D"
        if lim_rem is not None and float(lim_rem) < 2:
            return "C"
        return "A" if live else "B"

    if provider_id == "brave":
        if period_rem is not None and int(period_rem) <= 0:
            return "D"
        if period_rem is not None and int(period_rem) < 50:
            return "C"
        return "A" if live else "B"

    if provider_id == "opencode_zen":
        if live and chat_probe.get("ok"):
            return "A"
        return "B" if ready else "F"

    if provider_id in ("deepseek", "worker", "nvidia"):
        return "A" if live else "B"

    if provider_id == "telegram":
        return "B" if ready else "F"  # optional empty is F-grade but optional flag elsewhere

    if provider_id == "minimax":
        return "A" if live and ready else ("D" if ready else "F")

    return "B" if ready else "F"


def normalize_card(
    *,
    provider_id: str,
    title: str,
    description: str,
    ready: bool,
    error: str | None,
    keys: dict[str, str] | None,
    detail: dict[str, Any] | None,
    ops: list[str],
    live: bool,
    research_summary: dict[str, Any] | None = None,
    optional: bool = False,
) -> dict[str, Any]:
    """Canonical provider card for inventory / dashboard / API."""
    d = dict(detail or {})
    g = grade_provider(
        ready=ready, live=live, error=error, detail=d, provider_id=provider_id
    )
    caps = list(PROVIDER_CAPS.get(provider_id, ()))
    # Headline metrics for UI
    metrics: dict[str, Any] = {}
    for k in (
        "remaining",
        "allowed_spend",
        "min_remaining",
        "limit_remaining",
        "period_remaining",
        "period_limit",
        "model_count",
        "free_count",
        "tier",
    ):
        if k in d and d[k] is not None:
            metrics[k] = d[k]
    if isinstance(d.get("chat_probe"), dict):
        metrics["chat_ok"] = d["chat_probe"].get("ok")

    return {
        "id": provider_id,
        "title": title,
        "description": description,
        "ready": ready,
        "ok": ready and not error,
        "grade": g,
        "optional": optional or CAP_OPTIONAL in caps,
        "capabilities": caps,
        "error": error,
        "keys": keys or {},
        "metrics": metrics,
        "detail": d,
        "ops": ops,
        "research_summary": research_summary,
        "live": live,
    }


def sort_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {"A": 0, "B": 1, "C": 2, "D": 3, "?": 4, "F": 5}

    def key(c: dict[str, Any]) -> tuple:
        return (
            1 if c.get("optional") and not c.get("ready") else 0,
            order.get(str(c.get("grade") or "?"), 9),
            str(c.get("id") or ""),
        )

    return sorted(cards, key=key)
