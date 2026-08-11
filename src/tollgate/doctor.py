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
