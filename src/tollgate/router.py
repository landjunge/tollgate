"""
Provider-based intelligent routing with limits + health-aware ranking.

route(intent) → {provider, model, base, reason, fallbacks, ranking}
"""

from __future__ import annotations

from typing import Any

from tollgate.app_config import is_provider_enabled, load_config
from tollgate.gateway.admit import admit
from tollgate.gateway.context import RequestClass, RequestContext
from tollgate.schema import PROVIDER_CAPS


def _base_for(provider_id: str) -> str | None:
    return {
        "deepseek": "https://api.deepseek.com",
        "worker": "https://api.deepseek.com",
        "opencode_zen": "https://opencode.ai/zen/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "nvidia": "https://integrate.api.nvidia.com/v1",
        "brave": "https://api.search.brave.com",
        "elevenlabs": "https://api.elevenlabs.io",
        "minimax": "https://api.minimax.io/v1",
    }.get(provider_id)


def _health_map() -> dict[str, dict[str, Any]]:
    try:
        from tollgate.control_plane import provider_health

        return {str(r["provider"]): r for r in provider_health() if r.get("provider")}
    except Exception:  # noqa: BLE001
        return {}


def _rank_score(
    pick: dict[str, Any],
    *,
    health: dict[str, Any] | None,
    strategy: str,
    chain_index: int,
    chain_len: int,
) -> tuple[float, list[str]]:
    """
    Higher is better. Returns (score, human reasons for this pick).
    """
    h = health or {}
    health_score = float(h.get("score") if h.get("score") is not None else 50.0)
    # circuit open should never win if somehow admitted
    if h.get("circuit") == "open" or h.get("status") == "circuit_open":
        return -1000.0, ["circuit OPEN"]

    lat = h.get("latency_ms_avg")
    usd = float(h.get("usd") or 0.0)
    success = h.get("success_rate")
    reasons: list[str] = []

    # normalize components 0..100
    rel = health_score
    if success is not None:
        reasons.append(f"success {float(success):.0%}")
    else:
        reasons.append("no traffic yet (neutral health)")

    if lat is None:
        lat_score = 70.0  # unknown
    else:
        # 0ms → 100, 10s → ~0
        lat_score = max(0.0, min(100.0, 100.0 - (float(lat) / 100.0)))
        if float(lat) < 2000:
            reasons.append(f"latency ~{float(lat):.0f}ms")
        elif float(lat) >= 5000:
            reasons.append(f"latency elevated ~{float(lat):.0f}ms")

    # lower day spend → higher cost score (prefer cheaper lanes when equal reliability)
    cost_score = max(0.0, min(100.0, 100.0 - min(usd * 20.0, 100.0)))
    if usd <= 0.01:
        reasons.append("low day spend")
    else:
        reasons.append(f"${usd:.4f} day spend")

    # config chain order as soft bias (earlier = higher)
    order_score = 100.0 * (1.0 - (chain_index / max(chain_len, 1)))

    st = (strategy or "balanced").strip().lower()
    if st in ("reliability", "reliable", "health"):
        total = rel * 0.85 + lat_score * 0.10 + order_score * 0.05
        reasons.insert(0, "strategy=reliability")
    elif st in ("cost", "cost_optimized", "cheap"):
        total = rel * 0.35 + cost_score * 0.45 + lat_score * 0.10 + order_score * 0.10
        reasons.insert(0, "strategy=cost_optimized")
    else:
        # balanced: reliability first, then latency, cost, config order
        total = rel * 0.55 + lat_score * 0.20 + cost_score * 0.15 + order_score * 0.10
        reasons.insert(0, "strategy=balanced")

    # priority field from config (higher priority value wins slightly)
    prio = float(pick.get("priority") or 50)
    total += (prio - 50) * 0.05

    return total, reasons


def _rank_winners(
    winners: list[dict[str, Any]],
    *,
    chain: list[str],
    strategy: str,
    health_aware: bool,
) -> list[dict[str, Any]]:
    if not winners or not health_aware:
        return winners

    health = _health_map()
    chain_index = {p: i for i, p in enumerate(chain)}
    n = max(len(chain), 1)
    ranked: list[tuple[float, int, dict[str, Any]]] = []
    for i, pick in enumerate(winners):
        pid = str(pick.get("provider") or "")
        score, reasons = _rank_score(
            pick,
            health=health.get(pid),
            strategy=strategy,
            chain_index=int(chain_index.get(pid, i)),
            chain_len=n,
        )
        pick = dict(pick)
        pick["health_score"] = (health.get(pid) or {}).get("score")
        pick["health_status"] = (health.get(pid) or {}).get("status")
        pick["rank_score"] = round(score, 2)
        pick["rank_reasons"] = reasons
        pick["reason"] = (
            f"health-aware rank={score:.1f} "
            f"status={(health.get(pid) or {}).get('status')} · "
            + "; ".join(reasons[:4])
        )
        ranked.append((score, -i, pick))  # stable: higher score, then earlier collect

    ranked.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [p for _, __, p in ranked]


def route(
    service: Any,
    intent: str = "llm",
    *,
    tokens_est: int = 0,
    chars_est: int = 0,
    live: bool = False,
    prefer_free: bool | None = None,
) -> dict[str, Any]:
    """
    Pick best provider for intent under config + readiness + limits.

    When ``routing.health_aware`` is true (default), admitted candidates are
    ranked by reliability / latency / cost strategy — not only config order.

    Does not execute the call — only decides route.
    """
    cfg = load_config()
    intent = (intent or "llm").strip().lower()
    routing_cfg = cfg.get("routing") or {}
    intents = routing_cfg.get("intents") or {}
    chain = list(intents.get(intent) or intents.get("llm") or [])
    models = routing_cfg.get("models") or {}
    prefer_free = (
        bool(cfg.get("prefer_free", True)) if prefer_free is None else bool(prefer_free)
    )
    auto_failover = bool(cfg.get("auto_failover", True))
    health_aware = bool(routing_cfg.get("health_aware", True))
    strategy = str(routing_cfg.get("strategy") or "balanced").strip().lower()

    inv = service.inventory(live=live, use_cache=True)
    by_id = {c["id"]: c for c in (inv.get("providers") or [])}

    tried: list[dict[str, Any]] = []
    winners: list[dict[str, Any]] = []

    # optional reorder: free-capable first when prefer_free and intent is llm-ish
    if prefer_free and intent in ("llm", "free_llm", "paid_llm"):
        free_first = [p for p in chain if "free_llm" in PROVIDER_CAPS.get(p, ())]
        rest = [p for p in chain if p not in free_first]
        if intent == "free_llm":
            chain = free_first or chain
        elif intent == "llm":
            chain = free_first + rest

    for pid in chain:
        card = by_id.get(pid) or {}
        entry: dict[str, Any] = {"provider": pid}

        if not is_provider_enabled(pid):
            entry["skip"] = "disabled in keys_app.json"
            tried.append(entry)
            continue
        # Chaos / DR inject — treat as unavailable (prove failover)
        try:
            from tollgate.chaos import is_provider_in_chaos

            if is_provider_in_chaos(pid):
                entry["skip"] = "chaos inject — provider simulated down"
                entry["chaos"] = True
                tried.append(entry)
                continue
        except Exception:  # noqa: BLE001
            pass
        if not card.get("ready"):
            entry["skip"] = card.get("error") or "not ready"
            entry["grade"] = card.get("grade")
            tried.append(entry)
            continue
        if card.get("grade") in ("F", "D"):
            entry["skip"] = f"grade={card.get('grade')}"
            tried.append(entry)
            continue

        # L4 admission (limits + cost_guard + circuit)
        rclass = (
            RequestClass.FREE
            if (prefer_free and intent in ("llm", "free_llm"))
            else RequestClass.INTERACTIVE
        )
        decision = admit(
            pid,
            op=intent,
            tokens_est=tokens_est,
            chars_est=chars_est,
            model=str(models.get(pid) or ""),
            ctx=RequestContext(request_class=rclass),
        )
        if not decision.allowed:
            entry["skip"] = decision.reason
            entry["admit"] = decision.as_dict()
            tried.append(entry)
            if not auto_failover:
                break
            continue

        lim = decision.limits or {}

        # provider-specific soft gates
        if pid == "elevenlabs" and intent in ("tts", "media"):
            b = service.call("elevenlabs", "budget", cost=int(chars_est or 0))
            if not b.get("allowed"):
                entry["skip"] = b.get("error") or "EL budget"
                tried.append(entry)
                continue

        model = models.get(pid) or None
        if pid == "opencode_zen" and prefer_free:
            model = model or "deepseek-v4-flash-free"
        if pid == "openrouter":
            pcfg = (cfg.get("providers") or {}).get("openrouter") or {}
            if pcfg.get("free_only", True) or prefer_free:
                model = model or "openrouter/free"

        pick = {
            "provider": pid,
            "model": model,
            "base_url": _base_for(pid),
            "grade": card.get("grade"),
            "priority": ((cfg.get("providers") or {}).get(pid) or {}).get("priority"),
            "limits": {
                "remaining_calls": lim.get("remaining_calls"),
                "remaining_tokens": lim.get("remaining_tokens"),
                "remaining_chars": lim.get("remaining_chars"),
                "remaining_usd": lim.get("remaining_usd"),
            },
            "admit": decision.as_dict(),
            "soft_degrade": decision.soft_degrade,
            "metrics": card.get("metrics") or {},
            "reason": f"intent={intent} ready grade={card.get('grade')} admitted",
        }
        winners.append(pick)
        tried.append({**entry, "ok": True})
        if not auto_failover:
            break
        # collect more candidates for health ranking (cap)
        if len(winners) >= 8:
            break

    winners = _rank_winners(
        winners, chain=chain, strategy=strategy, health_aware=health_aware
    )
    # expose top 4 as primary + fallbacks
    primary = winners[0] if winners else None
    fallbacks = winners[1:4] if winners else []

    return {
        "ok": primary is not None,
        "intent": intent,
        "tokens_est": int(tokens_est or 0),
        "chars_est": int(chars_est or 0),
        "prefer_free": prefer_free,
        "auto_failover": auto_failover,
        "health_aware": health_aware,
        "strategy": strategy if health_aware else "config_order",
        "route": primary,
        "fallbacks": fallbacks,
        "ranking": [
            {
                "provider": w.get("provider"),
                "model": w.get("model"),
                "rank_score": w.get("rank_score"),
                "health_score": w.get("health_score"),
                "health_status": w.get("health_status"),
                "reasons": w.get("rank_reasons"),
            }
            for w in winners[:6]
        ],
        "tried": tried,
        "error": None if primary else f"no provider available for intent={intent}",
    }


def execute_routed(
    service: Any,
    intent: str,
    *,
    tokens_est: int = 0,
    chars_est: int = 0,
    **call_kwargs: Any,
) -> dict[str, Any]:
    """
    Route then invoke a default op for the intent.

    llm/free_llm → opencode chat or status
    search → brave search (needs query=)
    tts → elevenlabs budget check only (synthesis is external)
    """
    r = route(service, intent, tokens_est=tokens_est, chars_est=chars_est)
    if not r.get("ok") or not r.get("route"):
        return {"ok": False, "error": r.get("error"), "routing": r}

    pick = r["route"]
    pid = pick["provider"]
    model = pick.get("model")

    if intent in ("search",) and pid == "brave":
        q = call_kwargs.get("query") or call_kwargs.get("message") or ""
        out = service.call(
            "brave",
            "search",
            query=str(q),
            count=int(call_kwargs.get("count") or 5),
            _skip_limit=False,
        )
        out["routing"] = r
        return out

    if intent in ("tts",) and pid == "elevenlabs":
        out = service.call(
            "elevenlabs",
            "budget",
            cost=int(chars_est or call_kwargs.get("cost") or 0),
        )
        out["routing"] = r
        return out

    if intent in ("llm", "free_llm", "paid_llm") and pid == "opencode_zen":
        out = service.call(
            "opencode_zen",
            "chat",
            message=str(call_kwargs.get("message") or call_kwargs.get("query") or "hi"),
            model=str(call_kwargs.get("model") or model or "deepseek-v4-flash-free"),
            max_tokens=int(call_kwargs.get("max_tokens") or 64),
        )
        out["routing"] = r
        return out

    # default: status of chosen provider
    out = service.call(pid, "status", live=bool(call_kwargs.get("live", False)))
    out["routing"] = r
    return out
