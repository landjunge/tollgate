"""
Provider-based intelligent routing with limits + failover.

route(intent) → {provider, model, base, reason, fallbacks}
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

    Does not execute the call — only decides route.
    """
    cfg = load_config()
    intent = (intent or "llm").strip().lower()
    intents = (cfg.get("routing") or {}).get("intents") or {}
    chain = list(intents.get(intent) or intents.get("llm") or [])
    models = (cfg.get("routing") or {}).get("models") or {}
    prefer_free = (
        bool(cfg.get("prefer_free", True)) if prefer_free is None else bool(prefer_free)
    )
    auto_failover = bool(cfg.get("auto_failover", True))

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
        rclass = RequestClass.FREE if (prefer_free and intent in ("llm", "free_llm")) else RequestClass.INTERACTIVE
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
        # keep collecting fallbacks
        if len(winners) >= 4:
            break

    primary = winners[0] if winners else None
    return {
        "ok": primary is not None,
        "intent": intent,
        "tokens_est": int(tokens_est or 0),
        "chars_est": int(chars_est or 0),
        "prefer_free": prefer_free,
        "auto_failover": auto_failover,
        "route": primary,
        "fallbacks": winners[1:],
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
