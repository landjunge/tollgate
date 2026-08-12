"""
AI traffic control plane — product pane over ledger + circuits.

Pillars: Reliability · Cost · Control
Not agent memory — operational scores only.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from tollgate.app_config import is_provider_enabled, load_config
from tollgate.limits import check_consumer_limits, consumer_envelope
from tollgate.usage_ledger import load_usage


def _day_fraction() -> float:
    """Fraction of local calendar day elapsed (0..1], min 1/24 for projection."""
    now = datetime.now().astimezone()
    secs = now.hour * 3600 + now.minute * 60 + now.second
    return max(secs / 86400.0, 1.0 / 24.0)


def _circuit_map() -> dict[str, dict[str, Any]]:
    try:
        from tollgate.gateway.circuit import get_circuits

        by: dict[str, dict[str, Any]] = {}
        for row in get_circuits().snapshot() or []:
            if not isinstance(row, dict):
                continue
            pid = str(row.get("provider") or "").strip().lower()
            if not pid:
                continue
            # keep worst state for provider
            prev = by.get(pid)
            st = str(row.get("state") or "closed")
            rank = {"open": 2, "half_open": 1, "closed": 0}.get(st, 0)
            if prev is None or rank > {"open": 2, "half_open": 1, "closed": 0}.get(
                str(prev.get("state") or "closed"), 0
            ):
                by[pid] = row
        return by
    except Exception:  # noqa: BLE001
        return {}


def provider_health(*, root: Any = None) -> list[dict[str, Any]]:
    """
    Per-provider day health: success rate, avg latency, $, circuit, score.
    """
    usage = load_usage(root=root)
    providers = usage.get("providers") or {}
    circuits = _circuit_map()
    cfg = load_config()
    cfg_provs = cfg.get("providers") or {}

    ids = set(str(k) for k in providers.keys()) | set(str(k) for k in cfg_provs.keys())
    rows: list[dict[str, Any]] = []

    for pid in sorted(ids):
        p = providers.get(pid) if isinstance(providers.get(pid), dict) else {}
        calls = int((p or {}).get("calls") or 0)
        errors = int((p or {}).get("errors") or 0)
        ok_calls = max(0, calls - errors)
        success = (ok_calls / calls) if calls else None
        lat_n = int((p or {}).get("latency_ms_n") or 0)
        lat_sum = float((p or {}).get("latency_ms_sum") or 0.0)
        latency_avg = (lat_sum / lat_n) if lat_n else None
        usd = float((p or {}).get("usd") or 0.0)
        circ = circuits.get(pid) or {}
        cstate = str(circ.get("state") or "closed")
        enabled = is_provider_enabled(pid)

        # Score 0..100 — reliability first, then cost/latency soft factors
        if not enabled:
            score = 0.0
            status = "disabled"
        elif cstate == "open":
            score = 5.0
            status = "circuit_open"
        elif calls == 0:
            score = 50.0
            status = "idle"
        else:
            score = 100.0 * float(success or 0.0)
            if cstate == "half_open":
                score *= 0.7
                status = "degraded"
            elif (success or 1.0) < 0.9:
                status = "degraded"
            else:
                status = "healthy"
            if latency_avg is not None and latency_avg > 5000:
                score = max(0.0, score - 15.0)
            if latency_avg is not None and latency_avg > 15000:
                score = max(0.0, score - 15.0)

        rows.append(
            {
                "provider": pid,
                "enabled": enabled,
                "calls": calls,
                "errors": errors,
                "success_rate": None if success is None else round(success, 4),
                "latency_ms_avg": None if latency_avg is None else round(latency_avg, 1),
                "latency_ms_last": float((p or {}).get("latency_ms_last") or 0) or None,
                "usd": round(usd, 6),
                "circuit": cstate,
                "score": round(score, 1),
                "status": status,
            }
        )

    rows.sort(key=lambda r: (-float(r.get("score") or 0), str(r.get("provider"))))
    return rows


def consumer_burn(*, root: Any = None) -> list[dict[str, Any]]:
    """
    Per-consumer day spend + envelope + end-of-day projection.
    """
    usage = load_usage(root=root)
    consumers = usage.get("consumers") or {}
    cfg = load_config()
    envelopes = cfg.get("consumer_envelopes") or {}
    frac = _day_fraction()
    rows: list[dict[str, Any]] = []

    ids = set(str(k) for k in consumers.keys()) | {
        str(k) for k in envelopes.keys() if not str(k).startswith("_")
    }
    for cid in sorted(ids):
        if cid.startswith("_"):
            continue
        cu = consumers.get(cid) if isinstance(consumers.get(cid), dict) else {}
        used_usd = float((cu or {}).get("usd") or 0.0)
        calls = int((cu or {}).get("calls") or 0)
        tokens = int((cu or {}).get("tokens") or 0)
        env = consumer_envelope(cid)
        named = isinstance(envelopes.get(cid), dict) and not str(cid).startswith("_")
        max_usd = float(env.get("max_usd_day") or 0.0)
        max_calls = int(env.get("max_calls_day") or 0)
        lim = check_consumer_limits(cid)
        projected = used_usd / frac if used_usd > 0 else 0.0
        status = "ok"
        if max_usd > 0:
            if used_usd >= max_usd:
                status = "over_budget"
            elif projected > max_usd:
                status = "likely_over"
            elif used_usd >= max_usd * 0.8:
                status = "warn"
        elif not lim.get("allowed"):
            status = "blocked"

        # Named lane policy vs only _default inheritance (auto-discovered traffic)
        uses_default_only = not named and calls > 0

        rows.append(
            {
                "consumer": cid,
                "calls": calls,
                "tokens": tokens,
                "usd": round(used_usd, 6),
                "max_usd_day": max_usd or None,
                "max_calls_day": max_calls or None,
                "max_usd_request": float(env.get("max_usd_request") or 0) or None,
                "max_usd_hour": float(env.get("max_usd_hour") or 0) or None,
                "max_requests_minute": int(env.get("max_requests_minute") or 0) or None,
                "max_tool_calls": int(env.get("max_tool_calls") or 0) or None,
                "allowed_providers": list(env.get("allowed_providers") or []),
                "blocked_providers": list(env.get("blocked_providers") or []),
                "allowed_intents": list(env.get("allowed_intents") or []),
                "allowed_ops": list(env.get("allowed_ops") or []),
                "remaining_usd": lim.get("remaining_usd"),
                "remaining_calls": lim.get("remaining_calls"),
                "projected_usd_eod": round(projected, 4),
                "status": status,
                "allowed": bool(lim.get("allowed", True)),
                "named_policy": named,
                "uses_default_only": uses_default_only,
                "protected": bool(
                    max_usd
                    or max_calls
                    or env.get("max_tool_calls")
                    or env.get("max_usd_request")
                    or env.get("max_requests_minute")
                ),
            }
        )

    rows.sort(key=lambda r: -float(r.get("usd") or 0))
    return rows


def explain_route(route_result: dict[str, Any], *, root: Any = None) -> dict[str, Any]:
    """
    Human-readable reasons for a route() decision (Control pillar).

    Prefers rank_reasons from health-aware routing when present.
    """
    health = {r["provider"]: r for r in provider_health(root=root)}
    primary = route_result.get("route") if isinstance(route_result.get("route"), dict) else {}
    pid = str(route_result.get("provider") or primary.get("provider") or "")
    model = str(route_result.get("model") or primary.get("model") or "")
    reasons: list[str] = []
    checks: list[dict[str, Any]] = []

    if not route_result.get("ok"):
        return {
            "ok": False,
            "selected": None,
            "reasons": [str(route_result.get("error") or "no route")],
            "checks": [],
        }

    # From router ranking (best source of truth)
    rank_reasons = primary.get("rank_reasons") or []
    if isinstance(rank_reasons, list) and rank_reasons:
        reasons.extend(f"✓ {r}" for r in rank_reasons if r)
    if primary.get("rank_score") is not None:
        reasons.insert(
            0,
            f"selected {pid} (rank_score={primary.get('rank_score')}, "
            f"strategy={route_result.get('strategy') or 'balanced'})",
        )
        checks.append(
            {
                "ok": True,
                "code": "rank_score",
                "detail": primary.get("rank_score"),
            }
        )

    h = health.get(pid) or {}
    if h.get("status") == "healthy":
        reasons.append(f"✓ {pid} healthy (score {h.get('score')})")
        checks.append({"ok": True, "code": "healthy", "detail": h.get("status")})
    elif h.get("status") == "idle":
        reasons.append(f"✓ {pid} idle today — no error signal yet")
        checks.append({"ok": True, "code": "idle", "detail": "no day traffic"})
    elif h:
        reasons.append(f"· {pid} status={h.get('status')} score={h.get('score')}")
        checks.append(
            {
                "ok": h.get("status") not in ("circuit_open", "disabled"),
                "code": "status",
                "detail": h.get("status"),
            }
        )

    if h.get("success_rate") is not None:
        sr = float(h["success_rate"])
        checks.append({"ok": sr >= 0.9, "code": "success_rate", "detail": f"{sr:.1%}"})

    if h.get("latency_ms_avg") is not None:
        lat = float(h["latency_ms_avg"])
        checks.append({"ok": lat < 5000, "code": "latency", "detail": f"{lat:.0f}ms avg"})

    if route_result.get("prefer_free"):
        reasons.append("✓ prefer_free / free_llm intent")
        checks.append({"ok": True, "code": "prefer_free", "detail": True})

    # Compare to alternatives in ranking
    for row in (route_result.get("ranking") or [])[1:4]:
        if not isinstance(row, dict):
            continue
        fp = str(row.get("provider") or "")
        fh = health.get(fp) or {}
        if fh.get("circuit") == "open" or row.get("health_status") == "circuit_open":
            reasons.append(f"✗ {fp} circuit OPEN — not chosen")
            checks.append({"ok": False, "code": "alt_circuit", "detail": fp})
        elif fh.get("status") == "degraded" or row.get("health_status") == "degraded":
            reasons.append(f"✗ {fp} degraded (score {row.get('health_score')})")
            checks.append({"ok": False, "code": "alt_degraded", "detail": fp})
        elif row.get("rank_score") is not None and primary.get("rank_score") is not None:
            try:
                if float(row["rank_score"]) < float(primary["rank_score"]):
                    reasons.append(
                        f"· {fp} ranked lower ({row.get('rank_score')} < {primary.get('rank_score')})"
                    )
            except (TypeError, ValueError):
                pass

    for row in route_result.get("tried") or []:
        if isinstance(row, dict) and row.get("skip"):
            reasons.append(f"✗ skipped {row.get('provider')}: {row.get('skip')}")

    # Fallback list for clients
    fallbacks = []
    for fb in route_result.get("fallbacks") or []:
        if isinstance(fb, dict) and fb.get("provider"):
            fallbacks.append(
                {"provider": fb.get("provider"), "model": fb.get("model")}
            )

    return {
        "ok": True,
        "selected": {"provider": pid, "model": model},
        "reasons": reasons,
        "checks": checks,
        "fallbacks": fallbacks,
        "strategy": route_result.get("strategy"),
        "health_aware": route_result.get("health_aware"),
        "health": h or None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _audit_protection_stats(*, root: Any = None, max_lines: int = 5000) -> dict[str, int]:
    """Count recent admit denials / agent protection from audit.jsonl (ops only)."""
    out = {"admit_denies": 0, "agent_protection_blocks": 0, "failovers_hint": 0}
    try:
        from tollgate.audit_log import audit_summary

        s = audit_summary(max_scan=max_lines, root=root)
        out["admit_denies"] = int(s.get("admit_denies") or 0)
        out["agent_protection_blocks"] = int(s.get("agent_protection_blocks") or 0)
        # failover hops still need line walk for extra field
        from tollgate.audit_log import query_audit

        hops = 0
        for row in (query_audit(limit=200, event="usage", max_scan=max_lines, root=root).get("events") or []):
            extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
            if int(extra.get("failover_hops") or 0) > 1:
                hops += 1
        out["failovers_hint"] = hops
    except Exception:  # noqa: BLE001
        pass
    return out

def _protected_lane_count() -> int:
    """How many named consumer envelopes have any hard protection field."""
    cfg = load_config()
    envs = cfg.get("consumer_envelopes") or {}
    n = 0
    keys = (
        "max_usd_day",
        "max_calls_day",
        "max_usd_hour",
        "max_usd_request",
        "max_requests_minute",
        "max_tokens_request",
        "max_tool_calls",
    )
    for cid, block in envs.items():
        if str(cid).startswith("_") or not isinstance(block, dict):
            continue
        if any(float(block.get(k) or 0) > 0 for k in keys):
            n += 1
    return n


def control_snapshot(*, root: Any = None) -> dict[str, Any]:
    """Full control-plane pane for API / dashboard / CLI."""
    usage = load_usage(root=root)
    totals = usage.get("totals") or {}
    providers = provider_health(root=root)
    consumers = consumer_burn(root=root)
    open_circuits = sum(1 for p in providers if p.get("circuit") == "open")
    degraded = sum(1 for p in providers if p.get("status") in ("degraded", "circuit_open"))
    protected_cfg = _protected_lane_count()
    protected = max(
        protected_cfg,
        sum(
            1
            for c in consumers
            if c.get("max_usd_day") or c.get("max_calls_day")
        ),
    )
    over = [c for c in consumers if c.get("status") in ("over_budget", "likely_over", "warn")]
    day_usd = float(totals.get("usd") or 0.0)
    day_errors = int(totals.get("errors") or 0)
    day_calls = int(totals.get("calls") or 0)
    audit = _audit_protection_stats(root=root)
    blocks = int(audit.get("agent_protection_blocks") or 0)
    denies = int(audit.get("admit_denies") or 0)
    recent_deny_rows: list[dict[str, Any]] = []
    audit_top: dict[str, Any] = {}
    try:
        from tollgate.audit_log import audit_summary, recent_denies

        recent_deny_rows = recent_denies(limit=12, root=root)
        audit_top = audit_summary(max_scan=3000, root=root)
    except Exception:  # noqa: BLE001
        recent_deny_rows = []
        audit_top = {}

    # Attention feed (product: "3 things need attention")
    attention: list[dict[str, str]] = []
    for c in over[:5]:
        attention.append(
            {
                "level": "warn" if c.get("status") != "over_budget" else "error",
                "code": "budget_pressure",
                "message": (
                    f"Agent/lane «{c.get('consumer')}» status={c.get('status')} "
                    f"(${float(c.get('usd') or 0):.2f}"
                    + (
                        f" / ${c.get('max_usd_day')} day"
                        if c.get("max_usd_day")
                        else ""
                    )
                    + ")"
                ),
            }
        )
    for p in providers:
        if p.get("status") in ("degraded", "circuit_open"):
            attention.append(
                {
                    "level": "warn" if p.get("status") == "degraded" else "error",
                    "code": "provider_health",
                    "message": (
                        f"Provider «{p.get('provider')}» {p.get('status')} "
                        f"(score {p.get('score')}"
                        + (
                            f", success {float(p['success_rate'])*100:.0f}%"
                            if p.get("success_rate") is not None
                            else ""
                        )
                        + ")"
                    ),
                }
            )
    if open_circuits == 0 and day_errors > 0:
        attention.append(
            {
                "level": "ok",
                "code": "errors_absorbed",
                "message": f"{day_errors} provider error(s) recorded today — circuits currently closed",
            }
        )
    if blocks:
        attention.append(
            {
                "level": "ok",
                "code": "agent_protection",
                "message": f"{blocks} agent protection stop(s) prevented runaway spend",
            }
        )
    if protected == 0:
        attention.append(
            {
                "level": "warn",
                "code": "no_protection",
                "message": "No agent lanes have hard budgets/limits — set consumer-budget",
            }
        )
    chaos_blob: dict[str, Any] = {
        "active": [],
        "recovering": [],
        "last_report": None,
        "history": [],
    }
    try:
        from tollgate.chaos import status as chaos_status

        ch = chaos_status()
        chaos_blob = {
            "active": list(ch.get("active") or []),
            "recovering": list(ch.get("recovering") or []),
            "last_report": ch.get("last_report"),
            "history": list(ch.get("history") or []),
            "policy": ch.get("policy"),
        }
        if ch.get("active"):
            for inj in ch["active"][:3]:
                attention.append(
                    {
                        "level": "warn",
                        "code": "chaos_active",
                        "message": (
                            f"Chaos inject active on «{inj.get('provider')}» "
                            f"(until {inj.get('until')})"
                        ),
                    }
                )
        last = ch.get("last_report") if isinstance(ch.get("last_report"), dict) else None
        if last and last.get("survived"):
            attention.append(
                {
                    "level": "ok",
                    "code": "chaos_ok",
                    "message": (
                        f"Last DR test: {last.get('chaos_provider')} outage survived "
                        f"({last.get('successful')}/{last.get('requests_tested')} routes)"
                    ),
                }
            )
        elif not last:
            attention.append(
                {
                    "level": "warn",
                    "code": "chaos_untested",
                    "message": (
                        "Prove pending: no chaos test yet. Needs ≥2 enabled providers "
                        "in free_llm + keys, then: tollgate chaos test <provider> "
                        "(or Dashboard → Prove). Protect can still be OK."
                    ),
                    "fix": "#prove",
                }
            )
    except Exception:  # noqa: BLE001
        pass

    res_blob: dict[str, Any] | None = None
    try:
        from tollgate.resilience import resilience_score

        res_blob = resilience_score(root=root)
    except Exception:  # noqa: BLE001
        res_blob = None

    res_score = (res_blob or {}).get("score")
    headline = (
        f"${day_usd:.2f} spent today · "
        f"{blocks} agent stops · "
        f"{day_errors} provider errors · "
        f"{protected} agents protected"
    )
    freeze_blob: dict[str, Any] = {"frozen": False}
    try:
        from tollgate.freeze import freeze_status

        freeze_blob = freeze_status()
        if freeze_blob.get("frozen"):
            attention.insert(
                0,
                {
                    "level": "error",
                    "code": "admission_frozen",
                    "message": (
                        "ADMISSION FROZEN — "
                        + str(freeze_blob.get("reason") or "kill switch active")
                        + " · tollgate unfreeze"
                    ),
                },
            )
    except Exception:  # noqa: BLE001
        pass

    if res_score is not None:
        headline = f"Resilience {res_score}/100 · " + headline
    if freeze_blob.get("frozen"):
        headline = "⛔ FROZEN · " + headline
    if over:
        headline += f" · ⚠ {len(over)} need attention"

    return {
        "ok": True,
        "product": "Tollgate",
        "tagline": (
            "Safety layer between AI agents and the internet — "
            "Protect · Route · Prove"
        ),
        "promise": (
            "My AI agent must never go out of control: "
            "stop runaway cost and tool loops, survive provider failures, prove DR."
        ),
        "pillars": ["protect", "route", "prove"],
        "day": usage.get("day"),
        "updated_at": usage.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        "headline": headline,
        "summary": {
            "calls": day_calls,
            "errors": day_errors,
            "usd": round(day_usd, 6),
            "circuits_open": open_circuits,
            "providers_degraded": degraded,
            "consumers_protected": protected,
            "consumers_pressure": len(over),
            "agent_protection_blocks": blocks,
            "admit_denies": denies,
            "resilience_score": res_score,
            "frozen": bool(freeze_blob.get("frozen")),
            "failovers_hint": int(audit.get("failovers_hint") or 0),
        },
        # Product UX: "what Tollgate prevented" — first-success story
        "protection_summary": {
            "loop_stops": blocks,
            "requests_blocked": denies,
            "failovers_seen": int(audit.get("failovers_hint") or 0),
            "agents_protected": protected,
            "usd_spent_today": round(day_usd, 6),
            "tagline": "Connect your agent. Tollgate protects it automatically.",
        },
        "attention": attention[:12],
        "discovered_agents": [
            {
                "consumer": c.get("consumer"),
                "calls": c.get("calls"),
                "usd": c.get("usd"),
                "uses_default_only": True,
                "hint": "New traffic on default protection — name a policy if you want tighter limits",
            }
            for c in consumers
            if c.get("uses_default_only")
        ][:12],
        "activity": _activity_feed(
            recent_deny_rows=recent_deny_rows,
            chaos_blob=chaos_blob,
            consumers=consumers,
            open_circuits=open_circuits,
        ),
        "providers": providers,
        "consumers": consumers,
        "chaos": chaos_blob,
        "resilience": res_blob,
        "freeze": freeze_blob,
        "recent_denies": recent_deny_rows,
        "audit": {
            "admit_denies": denies,
            "agent_protection_blocks": blocks,
            "top_deny_reasons": (audit_top.get("top_deny_reasons") or [])[:8],
            "top_consumers": (audit_top.get("top_consumers") or [])[:8],
            "by_event": audit_top.get("by_event") or {},
        },
        "day_fraction": round(_day_fraction(), 4),
        "ts": time.time(),
    }


def _activity_feed(
    *,
    recent_deny_rows: list[dict[str, Any]],
    chaos_blob: dict[str, Any],
    consumers: list[dict[str, Any]],
    open_circuits: int,
) -> list[dict[str, str]]:
    """Short TODAY timeline for Overview (ops story, not analytics)."""
    items: list[dict[str, str]] = []
    for row in (recent_deny_rows or [])[:8]:
        if not isinstance(row, dict):
            continue
        who = str(row.get("consumer") or "agent")[:48]
        err = str(row.get("error") or row.get("reason") or "blocked")[:100]
        items.append(
            {
                "kind": "block",
                "icon": "🛑",
                "ts": str(row.get("ts") or ""),
                "text": f"{who}: {err}",
            }
        )
    last = chaos_blob.get("last_report") if isinstance(chaos_blob.get("last_report"), dict) else None
    if last:
        ok = bool(last.get("survived"))
        items.append(
            {
                "kind": "prove",
                "icon": "✓" if ok else "✗",
                "ts": str(last.get("finished_at") or last.get("ts") or ""),
                "text": (
                    f"Resilience test {'passed' if ok else 'failed'} "
                    f"({last.get('chaos_provider') or 'provider'})"
                ),
            }
        )
    for c in consumers:
        if c.get("status") == "warn":
            items.append(
                {
                    "kind": "budget",
                    "icon": "⚠",
                    "ts": "",
                    "text": f"«{c.get('consumer')}» near daily budget ({c.get('status')})",
                }
            )
    if open_circuits:
        items.append(
            {
                "kind": "circuit",
                "icon": "🔄",
                "ts": "",
                "text": f"{open_circuits} circuit(s) open — failover / cool-down active",
            }
        )
    return items[:14]
