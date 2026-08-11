"""
Compact operator status — one glance at Protect · Route · Prove.

CLI:  tollgate status
HTTP: GET /v1/status
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def desk_status(*, root: Any = None) -> dict[str, Any]:
    """
    Lightweight pane: freeze, resilience, spend, attention, last chaos.

    Does not replace control_snapshot — smaller, CLI-first.
    """
    from tollgate import __version__
    from tollgate.control_plane import control_snapshot
    from tollgate.freeze import freeze_status
    from tollgate.paths import path_snapshot

    snap = control_snapshot(root=root)
    fr = freeze_status()
    s = snap.get("summary") or {}
    res = snap.get("resilience") or {}
    chaos = snap.get("chaos") or {}
    last = chaos.get("last_report") if isinstance(chaos.get("last_report"), dict) else None
    att = snap.get("attention") or []
    urgent = [a for a in att if a.get("level") in ("error", "warn")]

    score = res.get("score")
    level = "ok"
    if fr.get("frozen"):
        level = "frozen"
    elif any(a.get("level") == "error" for a in att):
        level = "error"
    elif urgent:
        level = "warn"

    return {
        "ok": level in ("ok", "warn") and not fr.get("frozen"),
        "level": level,
        "version": __version__,
        "day": snap.get("day"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "headline": snap.get("headline"),
        "freeze": {
            "frozen": bool(fr.get("frozen")),
            "reason": fr.get("reason") or "",
            "source": fr.get("source"),
        },
        "resilience": {
            "score": score,
            "policy_compliant": res.get("policy_compliant"),
            "availability_estimate_pct": res.get("availability_estimate_pct"),
        },
        "spend": {
            "usd": s.get("usd"),
            "calls": s.get("calls"),
            "errors": s.get("errors"),
            "admit_denies": s.get("admit_denies"),
            "agent_protection_blocks": s.get("agent_protection_blocks"),
        },
        "route": {
            "circuits_open": s.get("circuits_open"),
            "providers_degraded": s.get("providers_degraded"),
        },
        "prove": {
            "last_chaos_survived": (last or {}).get("survived") if last else None,
            "last_chaos_provider": (last or {}).get("chaos_provider") if last else None,
            "chaos_history_n": len(chaos.get("history") or []),
        },
        "attention_n": len(att),
        "attention": att[:8],
        "portable": path_snapshot(),
        "hint": (
            "tollgate report · tollgate freeze status · tollgate doctor · "
            "GET /v1/control"
        ),
    }


def format_status_text(st: dict[str, Any] | None = None, *, root: Any = None) -> str:
    d = st if isinstance(st, dict) else desk_status(root=root)
    lvl = d.get("level") or "ok"
    mark = {"ok": "✓", "warn": "⚠", "error": "⛔", "frozen": "⛔"}.get(lvl, "·")
    fr = d.get("freeze") or {}
    res = d.get("resilience") or {}
    spend = d.get("spend") or {}
    route = d.get("route") or {}
    prove = d.get("prove") or {}

    lines = [
        f"tollgate status  {mark} {lvl}  ·  v{d.get('version')}  ·  day {d.get('day')}",
        "",
        f"  {d.get('headline') or '—'}",
        "",
        f"  freeze      {'ON — ' + str(fr.get('reason') or 'kill switch') if fr.get('frozen') else 'off'}",
        f"  resilience  {res.get('score') if res.get('score') is not None else '—'} / 100"
        + (
            f"  (policy {'ok' if res.get('policy_compliant') else 'gap'})"
            if res.get("policy_compliant") is not None
            else ""
        ),
        f"  spend       ${float(spend.get('usd') or 0):.4f}  ·  "
        f"{spend.get('calls') or 0} calls  ·  "
        f"{spend.get('agent_protection_blocks') or 0} agent stops  ·  "
        f"{spend.get('admit_denies') or 0} denies",
        f"  route       circuits open {route.get('circuits_open') or 0}  ·  "
        f"degraded {route.get('providers_degraded') or 0}",
    ]
    if prove.get("last_chaos_provider"):
        surv = prove.get("last_chaos_survived")
        lines.append(
            f"  prove       last DR {prove.get('last_chaos_provider')}: "
            f"{'survived' if surv else 'FAILED' if surv is False else '—'}"
            f"  ({prove.get('chaos_history_n') or 0} history)"
        )
    else:
        lines.append("  prove       no chaos test yet — tollgate chaos test <provider>")

    att = d.get("attention") or []
    if att:
        lines.append("")
        lines.append(f"  attention ({d.get('attention_n') or len(att)}):")
        for a in att[:6]:
            lm = {"ok": "✓", "error": "⛔", "warn": "⚠"}.get(a.get("level") or "", "·")
            lines.append(f"    {lm} {a.get('message')}")

    lines.append("")
    lines.append(f"  {d.get('hint')}")
    lines.append("")
    return "\n".join(lines)
