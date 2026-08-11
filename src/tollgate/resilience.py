"""
AI Resilience Score — continuous readiness, not just 'we have circuit breakers'.
"""

from __future__ import annotations

from typing import Any

from tollgate.app_config import is_provider_enabled, load_config
from tollgate.chaos import status as chaos_status
from tollgate.control_plane import consumer_burn, provider_health


def resilience_score(*, root: Any = None) -> dict[str, Any]:
    """
    Compute 0–100 AI resilience score + actionable warnings.

    Dimensions:
      reliability, failover, budget_control, provider_diversity, observability
    """
    cfg = load_config()
    health = provider_health(root=root)
    consumers = consumer_burn(root=root)
    routing = cfg.get("routing") or {}
    intents = routing.get("intents") or {}
    free_chain = list(intents.get("free_llm") or intents.get("llm") or [])
    paid_chain = list(intents.get("paid_llm") or intents.get("llm") or [])

    enabled = [p for p in health if p.get("enabled")]
    healthy = [p for p in enabled if p.get("status") in ("healthy", "idle")]
    open_c = [p for p in enabled if p.get("circuit") == "open"]
    degraded = [p for p in enabled if p.get("status") == "degraded"]

    # Reliability 0–100
    if not enabled:
        reliability = 20.0
    else:
        avg_score = sum(float(p.get("score") or 0) for p in enabled) / len(enabled)
        reliability = avg_score
        if open_c:
            reliability = min(reliability, 40.0)
        if degraded:
            reliability = min(reliability, reliability)  # already in score

    # Failover: auto_failover + multi-provider chains + last chaos test
    auto_fo = bool(cfg.get("auto_failover", True))
    multi_free = len([p for p in free_chain if is_provider_enabled(p)]) >= 2
    multi_paid = len([p for p in paid_chain if is_provider_enabled(p)]) >= 2
    chaos = chaos_status(root=root)
    last = chaos.get("last_report") if isinstance(chaos.get("last_report"), dict) else None
    failover = 40.0
    if auto_fo:
        failover += 20.0
    if multi_free or multi_paid:
        failover += 20.0
    if last and last.get("survived"):
        failover += 20.0
    elif last and last.get("ok"):
        failover += 10.0
    failover = min(100.0, failover)

    # Budget control
    envs = cfg.get("consumer_envelopes") or {}
    protected = 0
    for cid, block in envs.items():
        if str(cid).startswith("_") or not isinstance(block, dict):
            continue
        if any(
            float(block.get(k) or 0) > 0
            for k in (
                "max_usd_day",
                "max_usd_hour",
                "max_usd_request",
                "max_requests_minute",
                "max_tokens_request",
            )
        ):
            protected += 1
    budget = 30.0
    if float((cfg.get("cost_guard") or {}).get("max_usd_day_global") or 0) > 0:
        budget += 20.0
    if protected >= 1:
        budget += 30.0
    if protected >= 2:
        budget += 20.0
    budget = min(100.0, budget)

    # Provider diversity
    n_en = len(enabled)
    diversity = min(100.0, n_en * 25.0)  # 4+ providers → 100
    if n_en <= 1:
        diversity = 25.0

    # Observability: we have control plane / audit / metrics always → base high
    observability = 75.0
    if any(p.get("latency_ms_avg") for p in health):
        observability += 10.0
    if last:
        observability += 10.0
    observability = min(100.0, observability)

    overall = (
        reliability * 0.30
        + failover * 0.25
        + budget * 0.20
        + diversity * 0.15
        + observability * 0.10
    )

    warnings: list[str] = []
    ok_items: list[str] = []

    if not multi_free and not multi_paid:
        warnings.append("No multi-provider fallback chain — only one lane for LLM intents")
    else:
        ok_items.append("Multi-provider routing chain configured")

    if not auto_fo:
        warnings.append("auto_failover is disabled")
    else:
        ok_items.append("auto_failover enabled")

    if not last:
        warnings.append("No failover chaos test recorded — run: tollgate chaos test <provider>")
    elif last.get("survived"):
        ok_items.append(
            f"Failover tested for {last.get('chaos_provider')} — survived"
        )
    else:
        warnings.append(
            f"Last chaos test for {last.get('chaos_provider')} did not fully survive"
        )

    if protected == 0:
        warnings.append("No agent/consumer budget limits — set consumer-budget")
    else:
        ok_items.append(f"{protected} agent lane(s) have hard limits")

    for p in enabled:
        if p.get("status") == "circuit_open":
            warnings.append(f"Circuit OPEN on {p.get('provider')}")

    # Required fallbacks check per intent
    for intent_name, chain in (("free_llm", free_chain), ("llm", list(intents.get("llm") or []))):
        ready = [x for x in chain if is_provider_enabled(x)]
        if len(ready) < 2 and chain:
            warnings.append(f"Intent «{intent_name}» has fewer than 2 enabled providers")

    return {
        "ok": True,
        "product": "Tollgate",
        "title": "AI Resilience Score",
        "score": round(overall, 1),
        "dimensions": {
            "reliability": round(reliability, 1),
            "failover": round(failover, 1),
            "budget_control": round(budget, 1),
            "provider_diversity": round(diversity, 1),
            "observability": round(observability, 1),
        },
        "weights": {
            "reliability": 0.30,
            "failover": 0.25,
            "budget_control": 0.20,
            "provider_diversity": 0.15,
            "observability": 0.10,
        },
        "warnings": warnings,
        "ok_items": ok_items,
        "last_chaos_report": last,
        "active_chaos": chaos.get("active") or [],
        "enabled_providers": [p.get("provider") for p in enabled],
        "message": (
            f"Your AI infrastructure resilience is currently {overall:.1f}/100."
            if overall >= 70
            else f"Resilience {overall:.1f}/100 — address warnings before relying on production agents."
        ),
    }
