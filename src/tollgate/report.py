"""
Daily operator report — one pane for Protect · Route · Prove evidence.

CLI:  tollgate report
      tollgate report --format md
HTTP: GET /v1/report
MCP:  keys_report

Not agent memory — aggregates ledger, audit, resilience, chaos only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_report(*, root: Any = None) -> dict[str, Any]:
    """Assemble control-plane + audit + DR into a single report dict."""
    from tollgate.audit_log import audit_summary, recent_denies
    from tollgate.control_plane import control_snapshot
    from tollgate.paths import path_snapshot
    from tollgate.resilience import resilience_score

    snap = control_snapshot(root=root)
    res = resilience_score(root=root)
    summary = audit_summary(max_scan=5000, root=root)
    denies = recent_denies(limit=20, root=root)

    chaos = snap.get("chaos") or {}
    last = chaos.get("last_report") if isinstance(chaos.get("last_report"), dict) else None
    consumers = snap.get("consumers") or []
    providers = snap.get("providers") or []

    # Top burners by usd
    burners = sorted(
        [c for c in consumers if float(c.get("usd") or 0) > 0],
        key=lambda c: -float(c.get("usd") or 0),
    )[:10]
    sick = [
        p
        for p in providers
        if p.get("status") in ("degraded", "circuit_open") or p.get("circuit") == "open"
    ]

    prove = {
        "resilience_score": res.get("score"),
        "availability_estimate_pct": res.get("availability_estimate_pct"),
        "policy_compliant": res.get("policy_compliant"),
        "last_chaos": None,
        "chaos_history_n": len(chaos.get("history") or []),
        "active_chaos": chaos.get("active") or [],
    }
    if last:
        prove["last_chaos"] = {
            "provider": last.get("chaos_provider"),
            "survived": last.get("survived"),
            "message": last.get("message"),
            "successful": last.get("successful"),
            "requests_tested": last.get("requests_tested"),
            "recovery_time_ms_best": last.get("recovery_time_ms_best"),
            "extra_cost_usd": last.get("extra_cost_usd"),
            "finished_at": last.get("finished_at"),
        }

    s = snap.get("summary") or {}
    report: dict[str, Any] = {
        "ok": True,
        "product": "Tollgate",
        "version": _version(),
        "kind": "daily_operator_report",
        "day": snap.get("day"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "headline": snap.get("headline"),
        "tagline": snap.get("tagline"),
        "pillars": {
            "protect": {
                "usd_today": s.get("usd"),
                "calls": s.get("calls"),
                "admit_denies": s.get("admit_denies") or summary.get("admit_denies"),
                "agent_protection_blocks": s.get("agent_protection_blocks")
                or summary.get("agent_protection_blocks"),
                "consumers_protected": s.get("consumers_protected"),
                "top_deny_reasons": summary.get("top_deny_reasons") or [],
                "top_consumers_audit": summary.get("top_consumers") or [],
                "recent_denies": denies,
                "burners": burners,
            },
            "route": {
                "providers_degraded": s.get("providers_degraded"),
                "circuits_open": s.get("circuits_open"),
                "errors": s.get("errors"),
                "sick_providers": sick,
                "provider_health": providers[:20],
            },
            "prove": prove,
        },
        "attention": snap.get("attention") or [],
        "resilience": {
            "score": res.get("score"),
            "dimensions": res.get("dimensions"),
            "warnings": res.get("warnings") or [],
            "policy": res.get("policy"),
        },
        "portable": path_snapshot(),
        "hint": (
            "tollgate report --format md · GET /v1/report · "
            "tollgate chaos test <provider> · tollgate audit --summary"
        ),
    }
    return report


def format_report_markdown(report: dict[str, Any] | None = None, *, root: Any = None) -> str:
    """Human-readable daily brief for paste into Slack / status notes."""
    r = report if isinstance(report, dict) else build_report(root=root)
    p = r.get("pillars") or {}
    protect = p.get("protect") or {}
    route = p.get("route") or {}
    prove = p.get("prove") or {}
    res = r.get("resilience") or {}

    lines = [
        f"# Tollgate daily report — {r.get('day') or 'today'}",
        "",
        f"> {r.get('headline') or '—'}",
        "",
        f"_Generated {r.get('generated_at')} · v{r.get('version')}_",
        "",
        "## Protect",
        "",
        f"- **Spent today:** ${float(protect.get('usd_today') or 0):.4f}",
        f"- **Calls:** {protect.get('calls') or 0}",
        f"- **Admit denies:** {protect.get('admit_denies') or 0}",
        f"- **Agent protection stops:** {protect.get('agent_protection_blocks') or 0}",
        f"- **Lanes with caps:** {protect.get('consumers_protected') or 0}",
        "",
    ]

    burners = protect.get("burners") or []
    if burners:
        lines.append("### Top spenders")
        lines.append("")
        for c in burners[:8]:
            lines.append(
                f"- `{c.get('consumer')}` — ${float(c.get('usd') or 0):.4f}"
                f" (status {c.get('status')})"
            )
        lines.append("")

    reasons = protect.get("top_deny_reasons") or []
    if reasons:
        lines.append("### Top deny reasons")
        lines.append("")
        for row in reasons[:8]:
            lines.append(f"- {row.get('count')}× — {row.get('reason')}")
        lines.append("")

    recent = protect.get("recent_denies") or []
    if recent:
        lines.append("### Recent denies")
        lines.append("")
        for d in recent[:10]:
            prot = d.get("protection")
            why = d.get("error") or d.get("reason") or "deny"
            tag = f"[{prot}] " if prot else ""
            lines.append(
                f"- `{d.get('consumer')}` / {d.get('provider') or '—'} — {tag}{why}"
            )
        lines.append("")

    lines += [
        "## Route",
        "",
        f"- **Circuits open:** {route.get('circuits_open') or 0}",
        f"- **Providers degraded:** {route.get('providers_degraded') or 0}",
        f"- **Provider errors (day):** {route.get('errors') or 0}",
        "",
    ]
    sick = route.get("sick_providers") or []
    if sick:
        lines.append("### Unhealthy")
        lines.append("")
        for p in sick[:8]:
            lines.append(
                f"- `{p.get('provider')}` — {p.get('status')} "
                f"(circuit {p.get('circuit')}, score {p.get('score')})"
            )
        lines.append("")

    last = prove.get("last_chaos")
    lines += [
        "## Prove",
        "",
        f"- **Resilience score:** {prove.get('resilience_score') if prove.get('resilience_score') is not None else '—'} / 100",
        f"- **Availability est.:** {prove.get('availability_estimate_pct') if prove.get('availability_estimate_pct') is not None else '—'}%",
        f"- **Policy compliant:** {prove.get('policy_compliant')}",
        f"- **Chaos history entries:** {prove.get('chaos_history_n') or 0}",
        "",
    ]
    if last:
        ok = "✓ survived" if last.get("survived") else "⛔ failed"
        lines.append(
            f"- **Last DR:** {ok} `{last.get('provider')}` — "
            f"{last.get('successful')}/{last.get('requests_tested')} routes, "
            f"recovery {last.get('recovery_time_ms_best')} ms"
        )
        lines.append("")
    else:
        lines.append("- **Last DR:** none yet — `tollgate chaos test <provider>`")
        lines.append("")

    dims = res.get("dimensions") or {}
    if dims:
        lines.append("### Resilience dimensions")
        lines.append("")
        for k, v in dims.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

    att = r.get("attention") or []
    if att:
        lines.append("## Needs attention")
        lines.append("")
        for a in att[:12]:
            lvl = a.get("level") or "info"
            mark = {"ok": "✓", "error": "⛔", "warn": "⚠"}.get(lvl, "•")
            lines.append(f"- {mark} {a.get('message')}")
        lines.append("")

    lines += [
        "---",
        "",
        f"_CLI: `{r.get('hint')}`_",
        "",
    ]
    return "\n".join(lines)


def _version() -> str:
    try:
        from tollgate import __version__

        return str(__version__)
    except Exception:  # noqa: BLE001
        return "0.3.2"
