"""
tollgate doctor — first step after install / USB plug-in.

Human-readable issues + actions (no secrets in output).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from tollgate.app_config import config_path, load_config
from tollgate.config_validate import validate_config_dict
from tollgate.consumers import auth_status
from tollgate.paths import data_home, path_snapshot, pin_data_home_env, user_dir
from tollgate.secrets import is_usable_api_key, load_keys, resolve_key_txt_path


def run_doctor(*, live: bool = False, root: Path | None = None) -> dict[str, Any]:
    pin_data_home_env()
    issues: list[dict[str, str]] = []
    ok_items: list[str] = []

    snap = path_snapshot()
    home = data_home()
    ud = user_dir()
    ok_items.append(f"data_home={home}")
    if snap.get("portable"):
        ok_items.append("portable mode detected")
    if snap.get("usb"):
        ok_items.append("USB/removable mount path")

    # Key.txt
    kp = resolve_key_txt_path(root)
    if kp is None or not kp.is_file():
        issues.append(
            {
                "level": "error",
                "code": "no_key_txt",
                "message": f"No Key.txt under {ud}",
                "action": "Copy Key.txt.example → User/Key.txt and fill secrets",
            }
        )
    else:
        ok_items.append(f"Key.txt present ({kp.name})")
        keys = load_keys(root)
        # sample critical envs without values
        for env_name, label in (
            ("DEEPSEEK_API_KEY", "system LLM"),
            ("BRAVE_API_KEY", "search"),
            ("OPENCODE_API_KEY", "free chat (or OPENCODE_ZEN_API_KEY)"),
        ):
            alt = keys.get("OPENCODE_ZEN_API_KEY") if env_name.startswith("OPENCODE") else None
            val = keys.get(env_name) or alt or os.environ.get(env_name)
            if not is_usable_api_key(val):
                issues.append(
                    {
                        "level": "warn",
                        "code": f"missing_{env_name.lower()}",
                        "message": f"{label}: {env_name} not set or placeholder",
                        "action": f"Add {env_name}=… to User/Key.txt",
                    }
                )
            else:
                ok_items.append(f"{env_name} set")

    # Config
    cpath = config_path(root)
    cfg = load_config(force=True, root=root)
    _, cfg_errs = validate_config_dict(cfg)
    if cfg_errs:
        for e in cfg_errs:
            issues.append(
                {
                    "level": "error",
                    "code": "config_invalid",
                    "message": e,
                    "action": f"Edit {cpath}",
                }
            )
    else:
        ok_items.append("keys_app.json schema OK")

    # high-risk enabled without caps (also in validate)
    cg = cfg.get("cost_guard") or {}
    high = {str(x).lower() for x in (cg.get("high_risk_providers") or [])}
    for pid, p in (cfg.get("providers") or {}).items():
        if not isinstance(p, dict):
            continue
        if bool(p.get("enabled")) and (
            bool(p.get("high_risk")) or pid.lower() in high
        ):
            if float(p.get("max_usd_day") or 0) <= 0:
                issues.append(
                    {
                        "level": "error",
                        "code": "high_risk_no_cap",
                        "message": f"{pid} enabled high-risk without max_usd_day",
                        "action": f"Set providers.{pid}.max_usd_day (e.g. 1.0) or disable",
                    }
                )

    # Auth mode
    auth = auth_status()
    if auth.get("required"):
        ok_items.append(f"auth required ({auth.get('consumers_n')} consumers)")
    else:
        issues.append(
            {
                "level": "info",
                "code": "auth_open",
                "message": "Open auth mode (no consumers.json) — fine for local desk only",
                "action": "For n8n/multi-host: tollgate consumer-add n8n",
            }
        )

    # Agent protection / envelopes (count named lanes + _default)
    envelopes = cfg.get("consumer_envelopes") or {}
    _prot_keys = (
        "max_usd_day",
        "max_usd_hour",
        "max_usd_request",
        "max_requests_minute",
        "max_tokens_request",
        "max_tool_calls",
        "max_calls_day",
    )

    def _block_protected(block: Any) -> bool:
        if not isinstance(block, dict):
            return False
        return any(float(block.get(k) or 0) > 0 for k in _prot_keys)

    protected = 0
    default_on = _block_protected(envelopes.get("_default"))
    for cid, block in envelopes.items():
        if str(cid).startswith("_"):
            continue
        if _block_protected(block):
            protected += 1
    if default_on:
        ok_items.append("agent protection: _default envelope has caps (safe defaults)")
    if protected:
        ok_items.append(f"agent protection: {protected} named consumer lane(s) capped")
    if not default_on and not protected:
        issues.append(
            {
                "level": "warn",
                "code": "no_agent_protection",
                "message": "No consumer has spending/rate protection envelopes",
                "action": (
                    "tollgate consumer-budget n8n --max-usd-day 0.5 "
                    "--max-requests-minute 30 --max-usd-request 0.25 "
                    "(or restore consumer_envelopes._default from DEFAULT_CONFIG)"
                ),
            }
        )
    elif not default_on and auth.get("required"):
        issues.append(
            {
                "level": "info",
                "code": "default_envelope_open",
                "message": "_default envelope is unlimited — only named lanes are capped",
                "action": "Set consumer_envelopes._default max_usd_day (or leave named-only)",
            }
        )

    # Failover
    if bool(cfg.get("auto_failover", True)):
        ok_items.append("auto_failover enabled")
    else:
        issues.append(
            {
                "level": "warn",
                "code": "failover_off",
                "message": "auto_failover is false — provider outages will fail hard",
                "action": "Set auto_failover: true in keys_app.json",
            }
        )

    # Reliability policy (Prove pillar)
    try:
        from tollgate.app_config import is_provider_enabled
        from tollgate.chaos import reliability_policy, status as chaos_status

        pol = reliability_policy()
        req_fb = int(pol.get("required_fallbacks") or 2)
        routing = cfg.get("routing") or {}
        intents = routing.get("intents") or {}
        for intent_name in ("free_llm", "llm", "paid_llm"):
            chain = list(intents.get(intent_name) or [])
            if not chain:
                continue
            ready = [p for p in chain if is_provider_enabled(p)]
            if len(ready) < req_fb:
                issues.append(
                    {
                        "level": "warn",
                        "code": "policy_fallbacks",
                        "message": (
                            f"reliability.required_fallbacks={req_fb} but "
                            f"intent «{intent_name}» has only {len(ready)} enabled provider(s)"
                        ),
                        "action": (
                            f"Enable more providers in routing.intents.{intent_name} "
                            "or lower reliability.required_fallbacks"
                        ),
                    }
                )
            else:
                ok_items.append(
                    f"policy: {intent_name} has {len(ready)}≥{req_fb} fallbacks"
                )

        ch = chaos_status()
        last = ch.get("last_report") if isinstance(ch.get("last_report"), dict) else None
        if not last:
            issues.append(
                {
                    "level": "warn",
                    "code": "chaos_untested",
                    "message": "No failover chaos test recorded — DR not proven",
                    "action": "tollgate chaos test opencode_zen --requests 5",
                }
            )
        elif last.get("survived"):
            ok_items.append(
                f"DR proven: {last.get('chaos_provider')} outage survived "
                f"({last.get('successful')}/{last.get('requests_tested')})"
            )
            max_s = float(pol.get("max_failover_time_s") or 5)
            rec_ms = float(last.get("recovery_time_ms_best") or 0)
            if rec_ms > max_s * 1000:
                issues.append(
                    {
                        "level": "warn",
                        "code": "policy_failover_sla",
                        "message": (
                            f"Last recovery {rec_ms:.0f}ms exceeds "
                            f"reliability.max_failover_time_s={max_s}"
                        ),
                        "action": "Improve fallback latency or raise max_failover_time_s",
                    }
                )
        else:
            issues.append(
                {
                    "level": "error",
                    "code": "chaos_failed",
                    "message": (
                        f"Last chaos test for {last.get('chaos_provider')} "
                        "did not survive — app would fail on outage"
                    ),
                    "action": "Add fallbacks, enable auto_failover, re-run chaos test",
                }
            )

        if ch.get("active"):
            for inj in ch["active"][:3]:
                issues.append(
                    {
                        "level": "warn",
                        "code": "chaos_active",
                        "message": f"Chaos inject ACTIVE on {inj.get('provider')}",
                        "action": f"tollgate chaos stop {inj.get('provider')}",
                    }
                )
    except Exception as e:  # noqa: BLE001
        issues.append(
            {
                "level": "info",
                "code": "policy_check_skip",
                "message": f"reliability policy check skipped: {e}",
                "action": "see tollgate resilience",
            }
        )

    # Optional live diagnose from service
    service_diag: dict[str, Any] | None = None
    if live:
        try:
            from tollgate import get_keys_service

            service_diag = get_keys_service().diagnose(live=True)
            for issue in service_diag.get("issues") or []:
                if isinstance(issue, dict):
                    issues.append(
                        {
                            "level": str(issue.get("level") or "warn"),
                            "code": str(issue.get("code") or "service"),
                            "message": str(issue.get("message") or issue),
                            "action": str(issue.get("action") or "see dashboard"),
                        }
                    )
        except Exception as e:  # noqa: BLE001
            issues.append(
                {
                    "level": "warn",
                    "code": "diagnose_failed",
                    "message": str(e),
                    "action": "Run without --live or fix import/env",
                }
            )

    errors = sum(1 for i in issues if i.get("level") == "error")
    warns = sum(1 for i in issues if i.get("level") == "warn")
    return {
        "ok": errors == 0,
        "summary": {
            "errors": errors,
            "warnings": warns,
            "info": sum(1 for i in issues if i.get("level") == "info"),
        },
        "paths": snap,
        "config_path": str(cpath),
        "ok_items": ok_items,
        "issues": issues,
        "next": _next_steps(issues),
        "service_diagnose": service_diag,
    }


def _next_steps(issues: list[dict[str, str]]) -> list[str]:
    steps: list[str] = []
    codes = {i.get("code") for i in issues}
    if "no_key_txt" in codes:
        steps.append("Create User/Key.txt from Key.txt.example")
    if any(str(c).startswith("missing_") for c in codes):
        steps.append("Fill at least one free_llm key (OPENCODE_*) or DEEPSEEK_API_KEY")
    if "high_risk_no_cap" in codes or "config_invalid" in codes:
        steps.append("Fix keys_app.json (doctor lists fields)")
    if "auth_open" in codes:
        steps.append("Optional: tollgate consumer-add desk --admin")
    steps.append("tollgate serve   # or ./scripts/run.sh / docker compose up")
    steps.append("export OPENAI_BASE_URL=http://127.0.0.1:8787/v1")
    return steps


def format_doctor_text(report: dict[str, Any]) -> str:
    lines = ["# Tollgate doctor", ""]
    s = report.get("summary") or {}
    status = "PASS" if report.get("ok") else "FAIL"
    lines.append(f"Status: **{status}** (errors={s.get('errors')} warnings={s.get('warnings')})")
    lines.append("")
    if report.get("ok_items"):
        lines.append("## OK")
        for x in report["ok_items"]:
            lines.append(f"- {x}")
        lines.append("")
    if report.get("issues"):
        lines.append("## Issues")
        for i in report["issues"]:
            lines.append(
                f"- [{i.get('level')}] {i.get('message')} → {i.get('action')}"
            )
        lines.append("")
    lines.append("## Next")
    for n in report.get("next") or []:
        lines.append(f"1. {n}")
    lines.append("")
    return "\n".join(lines)
