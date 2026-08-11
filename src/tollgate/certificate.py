"""
AI Reliability Report — scorecard for the 10-minute / CTO screen.

Not a new product vertical: assembles existing control / resilience / chaos /
envelope signals into a simple PASS/FAIL certificate.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_certificate(*, root: Any = None, application: str = "") -> dict[str, Any]:
    from tollgate import __version__
    from tollgate.app_config import load_config
    from tollgate.control_plane import control_snapshot
    from tollgate.freeze import freeze_status
    from tollgate.resilience import resilience_score

    snap = control_snapshot(root=root)
    res = resilience_score(root=root)
    fr = freeze_status()
    cfg = load_config()
    envs = cfg.get("consumer_envelopes") or {}

    def _lane_protected(block: Any) -> bool:
        if not isinstance(block, dict):
            return False
        keys = (
            "max_usd_day",
            "max_usd_request",
            "max_tool_calls",
            "max_requests_minute",
            "max_usd_hour",
        )
        return any(float(block.get(k) or 0) > 0 for k in keys)

    named = [
        k
        for k, v in envs.items()
        if not str(k).startswith("_") and _lane_protected(v)
    ]
    default_ok = _lane_protected(envs.get("_default"))
    budget_pass = default_ok or bool(named)

    loop_pass = False
    for k, v in envs.items():
        if isinstance(v, dict) and int(v.get("max_tool_calls") or 0) > 0:
            loop_pass = True
            break
    if not loop_pass and isinstance(envs.get("_default"), dict):
        loop_pass = int((envs.get("_default") or {}).get("max_tool_calls") or 0) > 0

    chaos = snap.get("chaos") or {}
    last = chaos.get("last_report") if isinstance(chaos.get("last_report"), dict) else None
    if last is None:
        failover_status = "NOT_RUN"
        recovery_status = "NOT_RUN"
    elif last.get("survived"):
        failover_status = "PASS"
        recovery_status = "PASS"
    else:
        failover_status = "FAIL"
        recovery_status = "FAIL"

    audit = snap.get("audit") or {}
    audit_pass = True  # trail mechanism always present; evidence = denies optional
    # Prefer evidence of denies after a demo
    if int(audit.get("admit_denies") or 0) > 0:
        audit_evidence = "PASS"
    else:
        audit_evidence = "READY"  # system ok, no deny events yet

    checks = [
        {
            "id": "budget_protection",
            "label": "Budget Protection",
            "status": "PASS" if budget_pass else "FAIL",
            "detail": (
                f"{len(named)} named lane(s) + default"
                if budget_pass
                else "set consumer-budget or restore _default caps"
            ),
        },
        {
            "id": "agent_loop_protection",
            "label": "Agent Loop Protection",
            "status": "PASS" if loop_pass else "FAIL",
            "detail": "max_tool_calls on at least one envelope"
            if loop_pass
            else "set --max-tool-calls on a consumer",
        },
        {
            "id": "provider_failover",
            "label": "Provider Failover",
            "status": failover_status,
            "detail": (
                f"last chaos: {last.get('chaos_provider')} survived={last.get('survived')}"
                if last
                else (
                    "NOT_RUN — needs ≥2 enabled providers in free_llm chain + keys. "
                    "Then: tollgate chaos test opencode_zen --requests 8"
                )
            ),
            "next_step": (
                None
                if last
                else (
                    "1) tollgate doctor  2) enable 2nd provider / Key.txt  "
                    "3) tollgate chaos test <primary>  4) tollgate certificate"
                )
            ),
        },
        {
            "id": "recovery_test",
            "label": "Recovery Test",
            "status": recovery_status,
            "detail": (
                f"recovery_ms={last.get('recovery_time_ms_best')}"
                if last
                else "NOT_RUN — same as Provider Failover (included in chaos report)"
            ),
        },
        {
            "id": "audit_trail",
            "label": "Audit Trail",
            "status": audit_evidence,
            "detail": f"admit_denies={audit.get('admit_denies') or 0} in recent scan",
        },
    ]

    score = res.get("score")
    frozen = bool(fr.get("frozen"))
    if frozen:
        overall = "FROZEN"
    elif any(c["status"] == "FAIL" for c in checks if c["id"] in ("budget_protection", "agent_loop_protection")):
        overall = "NEEDS_PROTECT"
    elif failover_status == "FAIL":
        overall = "NEEDS_DR"
    elif failover_status == "NOT_RUN":
        overall = "PROTECT_OK_PROVE_PENDING"
    else:
        overall = "PASS"

    app_name = (application or "").strip() or "AI Agent (desk)"
    return {
        "ok": True,
        "product": "Tollgate",
        "title": "AI RELIABILITY REPORT",
        "application": app_name,
        "period": snap.get("day") or datetime.now(timezone.utc).strftime("%Y-%m"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": __version__,
        "overall": overall,
        "resilience_score": score,
        "frozen": frozen,
        "checks": checks,
        "headline": snap.get("headline"),
        "note": (
            "Certificate assembles live desk signals — not a legal audit. "
            "Run tollgate demo then certificate for a full card. "
            "NOT_RUN on failover is normal until chaos test with ≥2 providers."
        ),
        "prove_pending": failover_status == "NOT_RUN",
    }


def format_certificate_text(cert: dict[str, Any] | None = None, *, root: Any = None) -> str:
    c = cert if isinstance(cert, dict) else build_certificate(root=root)
    lines = [
        "══════════════════════════════════════════════",
        "  TOLLGATE",
        f"  {c.get('title')}",
        "══════════════════════════════════════════════",
        "",
        f"  Application:  {c.get('application')}",
        f"  Period:       {c.get('period')}",
        f"  Overall:      {c.get('overall')}",
        "",
    ]
    for ch in c.get("checks") or []:
        st = ch.get("status") or "?"
        mark = {"PASS": "✓", "FAIL": "✗", "NOT_RUN": "·", "READY": "·"}.get(st, "·")
        lines.append(f"  {mark} {ch.get('label'):<24} {st}")
        if ch.get("detail"):
            lines.append(f"      {ch.get('detail')}")
        if ch.get("next_step") and st == "NOT_RUN":
            lines.append(f"      next: {ch.get('next_step')}")
    score = c.get("resilience_score")
    lines += [
        "",
        f"  Resilience Score        {score if score is not None else '—'} / 100",
        "",
    ]
    if c.get("prove_pending"):
        lines.append("  · Prove pending (OK) — Protect can pass without chaos.")
        lines.append("    Need ≥2 providers + keys, then: tollgate chaos test <provider>")
        lines.append("")
    if c.get("frozen"):
        lines.append("  ⛔ ADMISSION FROZEN — unfreeze before production traffic")
        lines.append("")
    lines += [
        "  Protect · Route · Prove",
        "  Safety layer between AI agents and the internet.",
        "══════════════════════════════════════════════",
        "",
    ]
    return "\n".join(lines)
