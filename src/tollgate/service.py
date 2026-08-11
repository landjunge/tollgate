"""KeysService — flagship facade: inventory, dashboard, policy, ops."""

from __future__ import annotations

import os
import time
from typing import Any, Callable

from tollgate.secrets import is_usable_api_key
from tollgate import brave as brave_mod
from tollgate import deepseek as deepseek_mod
from tollgate import elevenlabs as el_mod
from tollgate import minimax as minimax_mod
from tollgate import google as google_mod
from tollgate import nvidia as nvidia_mod
from tollgate import opencode_zen as zen_mod
from tollgate import openrouter as openrouter_mod
from tollgate import providers as generic
from tollgate.base import mask_secret
from tollgate.catalog import FAMILIES, get_family, list_families
from tollgate.app_config import (
    is_provider_enabled,
    load_config,
    patch_config,
    provider_cfg,
    save_config,
)
from tollgate import auto_update as auto_update_mod
from tollgate.limits import check_limits
from tollgate.policy import preflight, recommend_model_route
from tollgate.research_notes import RESEARCH, RESEARCHED_AT, research_for
from tollgate.router import execute_routed, route as route_intent
from tollgate.schema import normalize_card, sort_cards
from tollgate.usage_ledger import (
    extract_tokens_from_result,
    record_usage,
    usage_summary,
)

_STATUS: dict[str, Callable[..., dict[str, Any]]] = {
    "deepseek": lambda **kw: deepseek_mod.status(worker=False, **kw),
    "worker": lambda **kw: deepseek_mod.status(worker=True, **kw),
    "brave": brave_mod.status,
    "elevenlabs": el_mod.status,
    "openrouter": openrouter_mod.status,
    "nvidia": nvidia_mod.status,
    "minimax": minimax_mod.status,
    "opencode_zen": zen_mod.status,
    "telegram": generic.telegram_status,
    "google": google_mod.status,
}

_OPS: dict[str, dict[str, Callable[..., Any]]] = {
    "elevenlabs": {
        "status": lambda **kw: el_mod.status(**kw),
        "budget": lambda cost=0, **_kw: el_mod.check_budget(cost=int(cost or 0)),
        "subscription": lambda force=False, **_kw: el_mod.fetch_subscription(
            force=bool(force)
        ),
        "ensure_budget": lambda cost=0, **_kw: el_mod.ensure_budget(cost=int(cost or 0)),
        "research": lambda **_kw: research_for("elevenlabs"),
    },
    "brave": {
        "status": lambda **kw: brave_mod.status(**kw),
        "search": lambda query="", count=5, country="DE", search_lang="de", **_kw: brave_mod.search(
            str(query),
            count=int(count or 5),
            country=str(country or "DE"),
            search_lang=str(search_lang or "de"),
        ),
        "quota": lambda force=False, **_kw: brave_mod.quota(force=bool(force)),
        "research": lambda **_kw: research_for("brave"),
    },
    "deepseek": {
        "status": lambda **kw: deepseek_mod.status(worker=False, **kw),
        "models": lambda **_kw: deepseek_mod.list_models(worker=False),
        "chat": lambda messages="hi", model=None, max_tokens=1024, temperature=0.7, **kw: deepseek_mod.chat(
            messages,
            model=model,
            max_tokens=int(max_tokens or 1024),
            temperature=float(temperature or 0.7),
            worker=False,
            **kw,
        ),
        "research": lambda **_kw: research_for("deepseek"),
    },
    "worker": {
        "status": lambda **kw: deepseek_mod.status(worker=True, **kw),
        "models": lambda **_kw: deepseek_mod.list_models(worker=True),
        "chat": lambda messages="hi", model=None, max_tokens=1024, temperature=0.7, **kw: deepseek_mod.chat(
            messages,
            model=model,
            max_tokens=int(max_tokens or 1024),
            temperature=float(temperature or 0.7),
            worker=True,
            **kw,
        ),
        "research": lambda **_kw: research_for("worker"),
    },
    "openrouter": {
        "status": lambda **kw: openrouter_mod.status(**kw),
        "credits": lambda **_kw: openrouter_mod.credits(),
        "models": lambda **_kw: openrouter_mod.models(),
        "chat": lambda messages="hi", model="openrouter/free", max_tokens=1024, temperature=0.7, **kw: openrouter_mod.chat(
            messages,
            model=str(model or "openrouter/free"),
            max_tokens=int(max_tokens or 1024),
            temperature=float(temperature or 0.7),
            **kw,
        ),
        "research": lambda **_kw: research_for("openrouter"),
    },
    "nvidia": {
        "status": lambda **kw: nvidia_mod.status(**kw),
        "models": lambda **_kw: nvidia_mod.list_models(),
        "research": lambda **_kw: research_for("nvidia"),
    },
    "minimax": {
        "status": lambda **kw: minimax_mod.status(**kw),
        "probe": lambda **_kw: minimax_mod.probe_key(),
        "research": lambda **_kw: research_for("minimax"),
    },
    "opencode_zen": {
        "status": lambda **kw: zen_mod.status(**kw),
        "models": lambda **_kw: zen_mod.list_models(),
        "chat": lambda message="hi", messages=None, model="deepseek-v4-flash-free", max_tokens=1024, temperature=0.7, **_kw: zen_mod.chat(
            message if messages is None else messages,
            model=str(model or "deepseek-v4-flash-free"),
            max_tokens=int(max_tokens or 1024),
            messages=messages,
            temperature=float(temperature or 0.7),
        ),
        "research": lambda **_kw: research_for("opencode_zen"),
    },
    "telegram": {
        "status": lambda **kw: generic.telegram_status(**kw),
        "research": lambda **_kw: research_for("telegram"),
    },
    "google": {
        "status": lambda **kw: google_mod.status(**kw),
        "research": lambda **_kw: research_for("google"),
    },
}


class KeysService:
    """
    Tollgate control plane: inventory / dashboard / diagnose / preflight /
    recommend / status / call / research / list_ops / route.
    """

    def __init__(self) -> None:
        self._inv_cache: dict[str, Any] = {"ts": 0.0, "live": None, "data": None}
        self._inv_ttl = 15.0  # short cache for dashboard spam

    # ── research ──────────────────────────────────────────────────────
    def research(self, provider_id: str | None = None) -> dict[str, Any]:
        if provider_id:
            pid = provider_id.strip().lower()
            note = research_for(pid)
            if not note:
                return {"ok": False, "error": f"no research for {provider_id}"}
            fam = get_family(pid)
            return {
                "ok": True,
                "provider": pid,
                "title": fam.title if fam else pid,
                "ops": list((_OPS.get(pid) or {}).keys()),
                "research": note,
                "researched_at": note.get("researched_at") or RESEARCHED_AT,
            }
        return {
            "ok": True,
            "researched_at": RESEARCHED_AT,
            "providers": {
                pid: {
                    "auth": n.get("auth"),
                    "probe": n.get("probe"),
                    "probe_kind": n.get("probe_kind"),
                    "special_ops": n.get("special_ops"),
                    "gotchas": n.get("gotchas"),
                    "errors": n.get("errors"),
                }
                for pid, n in RESEARCH.items()
            },
        }

    # ── inventory (normalized cards) ──────────────────────────────────
    def inventory(self, *, live: bool = False, use_cache: bool = True) -> dict[str, Any]:
        now = time.time()
        if (
            use_cache
            and self._inv_cache["data"] is not None
            and self._inv_cache["live"] is live
            and (now - float(self._inv_cache["ts"])) < self._inv_ttl
        ):
            out = dict(self._inv_cache["data"])
            out["cached"] = True
            return out

        cards: list[dict[str, Any]] = []
        for fam in list_families():
            fn = _STATUS.get(fam.id)
            note = research_for(fam.id)
            optional = fam.id == "telegram"
            if fn is None:
                ready = any(is_usable_api_key(os.environ.get(k)) for k in fam.env_keys)
                card = normalize_card(
                    provider_id=fam.id,
                    title=fam.title,
                    description=fam.description,
                    ready=ready,
                    error=None if ready else "no handler / key missing",
                    keys={k: mask_secret(os.environ.get(k)) for k in fam.env_keys},
                    detail={},
                    ops=list(fam.ops),
                    live=False,
                    research_summary={
                        "auth": note.get("auth"),
                        "probe": note.get("probe"),
                        "gotchas": (note.get("gotchas") or [])[:2],
                    }
                    if note
                    else None,
                    optional=optional,
                )
            else:
                do_live = bool(live and fam.probe)
                # telegram / presence families: live only if asked and probe true
                if live and fam.id == "telegram":
                    do_live = True
                st = fn(live=do_live)
                card = normalize_card(
                    provider_id=fam.id,
                    title=fam.title,
                    description=fam.description,
                    ready=bool(st.get("ready")),
                    error=st.get("error"),
                    keys=st.get("keys")
                    or {k: mask_secret(os.environ.get(k)) for k in fam.env_keys},
                    detail=st.get("detail") if isinstance(st.get("detail"), dict) else {},
                    ops=list((_OPS.get(fam.id) or {}).keys()) or list(fam.ops),
                    live=do_live,
                    research_summary={
                        "auth": note.get("auth"),
                        "probe": note.get("probe"),
                        "probe_kind": note.get("probe_kind"),
                        "gotchas": (note.get("gotchas") or [])[:2],
                    }
                    if note
                    else None,
                    optional=optional
                    or bool((st.get("detail") or {}).get("optional")),
                )
            cards.append(card)

        cards = sort_cards(cards)
        ready_n = sum(1 for c in cards if c.get("ready") and not c.get("optional"))
        core_n = sum(1 for c in cards if not c.get("optional"))
        grades = {g: sum(1 for c in cards if c.get("grade") == g) for g in "ABCDF?"}

        out = {
            "ok": True,
            "module": "tollgate",
            "researched_at": RESEARCHED_AT,
            "count": len(cards),
            "ready": ready_n,
            "core_count": core_n,
            "grades": grades,
            "providers": cards,
            "live": live,
            "cached": False,
            "note": (
                "live=false: presence/config. live=true: network probes "
                "(Brave metered+cached; EL subscription free; Zen free chat)."
            ),
        }
        self._inv_cache = {"ts": now, "live": live, "data": dict(out)}
        return out

    def dashboard(self, *, live: bool = False) -> dict[str, Any]:
        """
        Single pane of glass — grades, spend headroom, route advice, alerts.
        """
        inv = self.inventory(live=live)
        cards = inv.get("providers") or []
        alerts: list[dict[str, str]] = []
        for c in cards:
            if c.get("optional"):
                continue
            if c.get("grade") == "F":
                alerts.append(
                    {
                        "level": "error",
                        "provider": c["id"],
                        "message": c.get("error") or "not ready",
                    }
                )
            elif c.get("grade") == "D":
                alerts.append(
                    {
                        "level": "warn",
                        "provider": c["id"],
                        "message": c.get("error") or "degraded",
                    }
                )
            elif c.get("grade") == "C":
                alerts.append(
                    {
                        "level": "info",
                        "provider": c["id"],
                        "message": "constrained headroom — check metrics",
                    }
                )

        # Enrich spend metrics when not live (cheap local calls)
        el = next((c for c in cards if c["id"] == "elevenlabs"), None)
        if el and el.get("ready") and not live:
            try:
                b = el_mod.check_budget(cost=0)
                if b.get("ok"):
                    el.setdefault("metrics", {})
                    el["metrics"].update(
                        {
                            "remaining": b.get("remaining"),
                            "allowed_spend": b.get("allowed_spend"),
                            "min_remaining": b.get("min_remaining"),
                        }
                    )
            except Exception:  # noqa: BLE001
                pass

        route = recommend_model_route(self, prefer_free=True)
        smart = route_intent(self, "llm", live=False)
        usage = usage_summary()
        cfg = load_config()
        return {
            "ok": True,
            "module": "tollgate",
            "title": "Tollgate",
            "researched_at": RESEARCHED_AT,
            "summary": {
                "ready": inv.get("ready"),
                "core_count": inv.get("core_count"),
                "grades": inv.get("grades"),
                "alerts": len(alerts),
                "usage_day": usage.get("day"),
                "usage_calls": (usage.get("totals") or {}).get("calls"),
                "usage_tokens": (usage.get("totals") or {}).get("tokens"),
            },
            "alerts": alerts,
            "providers": cards,
            "llm_route": route,
            "smart_route": smart,
            "usage": usage,
            "config": {
                "prefer_free": cfg.get("prefer_free"),
                "auto_failover": cfg.get("auto_failover"),
                "auto_update": cfg.get("auto_update"),
                "providers_enabled": {
                    k: bool(v.get("enabled", True))
                    for k, v in (cfg.get("providers") or {}).items()
                },
            },
            "auto_update": auto_update_mod.status(),
            "live": live,
            "circuits": __import__(
                "tollgate.gateway.circuit", fromlist=["get_circuits"]
            ).get_circuits().snapshot()[:20],
            "architecture": "docs/keys/ARCHITECTURE.md",
            "ops_hint": {
                "route": "keys_call provider=keys op=route intent=llm|free_llm|search|tts",
                "tts": "keys_call elevenlabs budget",
                "search": "keys_web_search (gateway-sealed)",
                "free_llm": "keys_zen_chat model=deepseek-v4-flash-free",
                "usage": "GET /api/keys/usage",
                "config": "GET|POST /api/keys/config",
                "masterpiece": "L4 admit + circuit + cost_guard + distill SSoT",
            },
        }

    def diagnose(self, *, live: bool = True) -> dict[str, Any]:
        """Deep check: dead keys, low balances, config mistakes, next actions."""
        inv = self.inventory(live=live)
        issues: list[dict[str, Any]] = []
        actions: list[str] = []

        for c in inv.get("providers") or []:
            pid = c["id"]
            if c.get("optional") and not c.get("ready"):
                continue
            if not c.get("ready"):
                issues.append(
                    {
                        "severity": "error",
                        "provider": pid,
                        "issue": c.get("error") or "not ready",
                        "grade": c.get("grade"),
                    }
                )
                if pid == "minimax":
                    actions.append("Create new MiniMax API key at platform.minimax.io")
                elif pid == "openrouter":
                    actions.append("Fix OpenRouter key / add credits at openrouter.ai")
                elif pid == "telegram":
                    pass
                else:
                    actions.append(f"Check {pid} key in User/Key.txt")
            elif c.get("grade") == "C":
                issues.append(
                    {
                        "severity": "warn",
                        "provider": pid,
                        "issue": "low headroom",
                        "metrics": c.get("metrics"),
                        "grade": "C",
                    }
                )
                if pid == "openrouter":
                    actions.append("Top up OpenRouter or raise per-key limit")
                if pid == "elevenlabs":
                    actions.append("EL reserve near floor — wait for monthly reset or lower MIN_REMAINING")
                if pid == "brave":
                    actions.append("Brave monthly quota low — throttle web_search")

        # Special: OpenRouter chain tried
        if live:
            cr = openrouter_mod.credits()
            if cr.get("tried"):
                dead = [t for t in cr["tried"] if not t.get("ok")]
                if dead:
                    issues.append(
                        {
                            "severity": "info",
                            "provider": "openrouter",
                            "issue": f"{len(dead)} dead key alias(es) in chain",
                            "tried": dead,
                        }
                    )

        route = recommend_model_route(self, prefer_free=True)
        return {
            "ok": True,
            "healthy": not any(i.get("severity") == "error" for i in issues),
            "issues": issues,
            "actions": list(dict.fromkeys(actions)),  # dedupe preserve order
            "llm_route": route,
            "grades": inv.get("grades"),
            "live": live,
        }

    def preflight(
        self, intent: str = "any", *, cost: int = 0, live: bool = False
    ) -> dict[str, Any]:
        return preflight(self, intent=intent, cost=cost, live=live)

    def recommend(self, *, prefer_free: bool = True) -> dict[str, Any]:
        return recommend_model_route(self, prefer_free=prefer_free)

    def status(self, provider_id: str, *, live: bool = True) -> dict[str, Any]:
        pid = (provider_id or "").strip().lower()
        fam = get_family(pid)
        if fam is None:
            return {"ok": False, "error": f"unknown provider: {provider_id}"}
        fn = _STATUS.get(pid)
        if fn is None:
            return {"ok": False, "error": f"no status handler: {pid}"}
        do_live = bool(live and fam.probe) if live else False
        if live and pid == "telegram":
            do_live = True
        st = fn(live=do_live)
        note = research_for(pid)
        card = normalize_card(
            provider_id=pid,
            title=fam.title,
            description=fam.description,
            ready=bool(st.get("ready")),
            error=st.get("error"),
            keys=st.get("keys"),
            detail=st.get("detail") if isinstance(st.get("detail"), dict) else {},
            ops=list((_OPS.get(pid) or {}).keys()),
            live=do_live,
            research_summary={
                "auth": note.get("auth"),
                "probe": note.get("probe"),
                "gotchas": (note.get("gotchas") or [])[:3],
            },
            optional=pid == "telegram",
        )
        card["research"] = note
        card["ok"] = card["ready"]
        return card

    def call(self, provider_id: str, op: str, **kwargs: Any) -> dict[str, Any]:
        pid = (provider_id or "").strip().lower()
        oname = (op or "status").strip().lower()
        skip_limit = bool(kwargs.pop("_skip_limit", False))
        tokens_est = int(kwargs.pop("tokens_est", 0) or 0)
        chars_est = int(kwargs.pop("chars_est", 0) or 0)
        # estimate chars/tokens from message/query/messages for chat/search
        if not chars_est and oname in ("chat", "search", "budget"):
            raw = str(kwargs.get("message") or kwargs.get("query") or "")
            msgs = kwargs.get("messages")
            if not raw and isinstance(msgs, list):
                raw = " ".join(str(m.get("content") or "") for m in msgs if isinstance(m, dict))
            if oname == "budget":
                chars_est = int(kwargs.get("cost") or 0)
            elif raw:
                chars_est = len(raw)
                if oname == "chat" and not tokens_est:
                    tokens_est = max(16, len(raw) // 3)

        # Service-level meta ops
        if pid in ("_", "keys", "system", "meta") or oname in (
            "dashboard",
            "diagnose",
            "preflight",
            "recommend",
            "inventory",
            "route",
            "usage",
            "config",
            "auto_update",
        ):
            if oname == "dashboard":
                return self.dashboard(live=bool(kwargs.get("live")))
            if oname == "diagnose":
                return self.diagnose(live=bool(kwargs.get("live", True)))
            if oname == "preflight":
                return self.preflight(
                    str(kwargs.get("intent") or "any"),
                    cost=int(kwargs.get("cost") or 0),
                    live=bool(kwargs.get("live")),
                )
            if oname == "recommend":
                return self.recommend(prefer_free=bool(kwargs.get("prefer_free", True)))
            if oname == "inventory":
                return self.inventory(live=bool(kwargs.get("live")))
            if oname == "route":
                return self.route(
                    str(kwargs.get("intent") or "llm"),
                    tokens_est=tokens_est,
                    chars_est=chars_est,
                    live=bool(kwargs.get("live")),
                )
            if oname == "usage":
                return self.usage()
            if oname == "config":
                if kwargs.get("patch") is not None:
                    return self.set_config(kwargs.get("patch") or {})
                return self.get_config()
            if oname == "auto_update":
                act = str(kwargs.get("action") or "status")
                return self.auto_update(act)

        fam = get_family(pid)
        if fam is None:
            return {"ok": False, "error": f"unknown provider: {provider_id}"}

        if not is_provider_enabled(pid) and oname not in ("status", "research"):
            return {
                "ok": False,
                "error": f"provider {pid} disabled in keys_app.json",
                "provider": pid,
                "op": oname,
            }

        # Enforce call/token limits on mutating / cost ops
        cost_ops = {
            "search",
            "chat",
            "budget",
            "ensure_budget",
            "quota",
            "models",
            "credits",
            "probe",
            "subscription",
        }
        if not skip_limit and oname in cost_ops:
            lim = check_limits(
                pid, tokens_est=tokens_est, chars_est=chars_est, op=oname
            )
            if not lim.get("allowed"):
                return {
                    "ok": False,
                    "error": lim.get("reason") or "limit exceeded",
                    "provider": pid,
                    "op": oname,
                    "limits": lim,
                }

        # EL min_remaining from config overrides env if set
        if pid == "elevenlabs" and oname in ("budget", "ensure_budget"):
            pcfg = provider_cfg("elevenlabs")
            if pcfg.get("min_remaining") is not None:
                os.environ.setdefault(
                    "ELEVENLABS_MIN_REMAINING", str(int(pcfg["min_remaining"]))
                )

        ops = _OPS.get(pid) or {}
        fn = ops.get(oname)
        if fn is None:
            return {
                "ok": False,
                "error": f"unknown op '{op}' for {pid}",
                "available": list(ops.keys()) or list(fam.ops),
            }
        # Only pass kwargs the op likely accepts
        try:
            import inspect

            sig = inspect.signature(fn)
            if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                call_kw = kwargs
            else:
                allowed = set(sig.parameters.keys())
                call_kw = {k: v for k, v in kwargs.items() if k in allowed}
        except Exception:  # noqa: BLE001
            call_kw = kwargs
        try:
            result = fn(**call_kw)
        except TypeError as e:
            return {"ok": False, "error": f"bad args for {pid}.{oname}: {e}"}
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

        if isinstance(result, dict):
            out = dict(result)
            out.setdefault("provider", pid)
            out.setdefault("op", oname)
            # Usage accounting
            cfg = load_config()
            if bool(cfg.get("record_usage", True)) and oname in cost_ops:
                tin, tout, ch = extract_tokens_from_result(out)
                if oname == "search":
                    ch = 0
                    tin, tout = 0, 0
                if oname == "budget" and chars_est:
                    ch = max(ch, 0)  # budget check itself is free
                if oname == "chat" and not (tin or tout):
                    # estimate if API omitted usage
                    msg = str(kwargs.get("message") or "")
                    tin = max(tin, len(msg) // 3)
                    tout = max(tout, int(kwargs.get("max_tokens") or 16) // 2)
                # Don't count pure status-like budget=0 as chars spend
                if oname == "budget":
                    ch = 0
                try:
                    used = record_usage(
                        pid,
                        op=oname,
                        tokens_in=tin,
                        tokens_out=tout,
                        chars=ch,
                        error=not bool(out.get("ok", True)),
                        meta={"model": out.get("model") or kwargs.get("model")},
                    )
                    out["usage_today"] = {
                        "calls": used.get("calls"),
                        "tokens": used.get("tokens"),
                        "chars": used.get("chars"),
                    }
                    lim2 = check_limits(pid, tokens_est=0, chars_est=0, op=oname)
                    out["limits_remaining"] = {
                        "calls": lim2.get("remaining_calls"),
                        "tokens": lim2.get("remaining_tokens"),
                        "chars": lim2.get("remaining_chars"),
                    }
                except Exception:  # noqa: BLE001
                    pass
            return out
        return {"ok": True, "provider": pid, "op": oname, "result": result}

    # ── mini-app surfaces ─────────────────────────────────────────────
    def route(
        self,
        intent: str = "llm",
        *,
        tokens_est: int = 0,
        chars_est: int = 0,
        live: bool = False,
        prefer_free: bool | None = None,
    ) -> dict[str, Any]:
        r = route_intent(
            self,
            intent,
            tokens_est=tokens_est,
            chars_est=chars_est,
            live=live,
            prefer_free=prefer_free,
        )
        # Flatten primary for HTTP/OpenAI clients that expect top-level provider/model
        primary = r.get("route") if isinstance(r.get("route"), dict) else None
        if primary:
            r.setdefault("provider", primary.get("provider"))
            r.setdefault("model", primary.get("model"))
            r.setdefault("base_url", primary.get("base_url"))
        return r

    def route_execute(self, intent: str, **kwargs: Any) -> dict[str, Any]:
        return execute_routed(self, intent, **kwargs)

    def usage(self) -> dict[str, Any]:
        return usage_summary()

    def get_config(self) -> dict[str, Any]:
        return {"ok": True, "config": load_config(force=True)}

    def set_config(self, patch: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(patch, dict):
            return {"ok": False, "error": "config patch must be object"}
        cfg = patch_config(patch)
        return {"ok": True, "config": cfg}

    def replace_config(self, cfg: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "config": save_config(cfg if isinstance(cfg, dict) else {})}

    def check_provider_limits(
        self, provider_id: str, *, tokens_est: int = 0, chars_est: int = 0
    ) -> dict[str, Any]:
        return check_limits(provider_id, tokens_est=tokens_est, chars_est=chars_est)

    def auto_update(self, action: str = "status") -> dict[str, Any]:
        act = (action or "status").strip().lower()
        if act == "start":
            return auto_update_mod.start(get_keys_service)
        if act == "stop":
            return auto_update_mod.stop()
        if act == "once":
            return auto_update_mod.run_once(get_keys_service)
        return {"ok": True, **auto_update_mod.status()}

    def app_status(self) -> dict[str, Any]:
        """Compact mini-app status for UI."""
        cfg = load_config()
        usage = usage_summary()
        return {
            "ok": True,
            "app": "tollgate",
            "researched_at": RESEARCHED_AT,
            "prefer_free": cfg.get("prefer_free"),
            "auto_failover": cfg.get("auto_failover"),
            "auto_update": auto_update_mod.status(),
            "usage": usage.get("totals"),
            "usage_day": usage.get("day"),
            "config_path": str(
                __import__("tollgate.app_config", fromlist=["config_path"]).config_path()
            ),
            "usage_path": str(
                __import__("tollgate.usage_ledger", fromlist=["usage_path"]).usage_path()
            ),
        }

    def list_ops(self, provider_id: str | None = None) -> dict[str, Any]:
        if provider_id:
            pid = provider_id.strip().lower()
            fam = get_family(pid)
            if not fam:
                return {"ok": False, "error": f"unknown provider: {provider_id}"}
            return {
                "ok": True,
                "provider": pid,
                "ops": list((_OPS.get(pid) or {}).keys()) or list(fam.ops),
                "title": fam.title,
                "research": research_for(pid),
            }
        meta = [
            "dashboard",
            "diagnose",
            "preflight",
            "recommend",
            "inventory",
            "route",
            "usage",
            "config",
            "auto_update",
        ]
        return {
            "ok": True,
            "meta_ops": meta,
            "providers": {
                f.id: {
                    "title": f.title,
                    "ops": list((_OPS.get(f.id) or {}).keys()) or list(f.ops),
                }
                for f in FAMILIES
            },
        }

    def summary(self) -> dict[str, Any]:
        """Tiny snapshot for hub.snapshot() — never expensive network."""
        inv = self.inventory(live=False, use_cache=True)
        usage = usage_summary()
        return {
            "ready": inv.get("ready"),
            "core_count": inv.get("core_count"),
            "grades": inv.get("grades"),
            "researched_at": RESEARCHED_AT,
            "usage_day": usage.get("day"),
            "usage_tokens": (usage.get("totals") or {}).get("tokens"),
            "usage_calls": (usage.get("totals") or {}).get("calls"),
            "auto_update": auto_update_mod.status().get("running"),
            "providers": [
                {
                    "id": c["id"],
                    "grade": c.get("grade"),
                    "ready": c.get("ready"),
                    "optional": c.get("optional"),
                }
                for c in (inv.get("providers") or [])
            ],
        }


_SERVICE: KeysService | None = None


def get_keys_service() -> KeysService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = KeysService()
    return _SERVICE
