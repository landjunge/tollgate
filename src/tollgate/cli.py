"""tollgate CLI entry."""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        prog="tollgate",
        description="Tollgate — AI reliability & control plane for agents",
    )
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("serve", help="Run HTTP server (uvicorn)")
    sub.add_parser("mcp", help="Run MCP stdio server")
    sub.add_parser("health", help="Print local health JSON (paths + auth mode)")
    sub.add_parser(
        "control",
        help="Control plane snapshot (provider health + consumer burn + headline)",
    )
    sub.add_parser(
        "resilience",
        help="AI Resilience Score (0–100) + warnings",
    )
    ch = sub.add_parser(
        "chaos",
        help="Chaos / DR: inject provider outage or run failover test",
    )
    ch.add_argument(
        "action",
        choices=["status", "start", "stop", "test"],
        help="status | start | stop | test",
    )
    ch.add_argument("provider", nargs="?", default="", help="provider id (e.g. opencode_zen)")
    ch.add_argument(
        "--duration",
        default="5m",
        help="inject duration: 30s, 5m, 1h (default 5m)",
    )
    ch.add_argument("--requests", type=int, default=5, help="probes for chaos test")
    ch.add_argument("--intent", default="free_llm", help="route intent for test")
    ch.add_argument("--live-chat", action="store_true", help="also send tiny chats (costs)")
    ch.add_argument("--all", action="store_true", help="stop all injects")
    sub.add_parser("paths", help="Print portable path snapshot")

    cadd = sub.add_parser("consumer-add", help="Add HTTP consumer (id:secret)")
    cadd.add_argument("id", help="consumer id (e.g. n8n, gnom)")
    cadd.add_argument("--admin", action="store_true", help="allow /v1/config")
    cadd.add_argument("--secret", default="", help="optional fixed secret")
    cadd.add_argument("--label", default="", help="display label")

    cbud = sub.add_parser(
        "consumer-budget",
        help="Set / list day envelopes + agent protection (consumer_envelopes)",
    )
    cbud.add_argument(
        "id",
        nargs="?",
        default="",
        help="consumer id (omit with --list)",
    )
    cbud.add_argument("--list", action="store_true", help="list all envelopes + usage")
    cbud.add_argument("--max-calls-day", type=int, default=None, dest="max_calls_day")
    cbud.add_argument("--max-tokens-day", type=int, default=None, dest="max_tokens_day")
    cbud.add_argument("--max-usd-day", type=float, default=None, dest="max_usd_day")
    cbud.add_argument("--max-usd-request", type=float, default=None, dest="max_usd_request")
    cbud.add_argument("--max-usd-hour", type=float, default=None, dest="max_usd_hour")
    cbud.add_argument(
        "--max-requests-minute", type=int, default=None, dest="max_requests_minute"
    )
    cbud.add_argument(
        "--max-tokens-request", type=int, default=None, dest="max_tokens_request"
    )
    cbud.add_argument("--max-tool-calls", type=int, default=None, dest="max_tool_calls")
    cbud.add_argument(
        "--allow-provider",
        action="append",
        default=None,
        dest="allow_providers",
        help="L3 scope: allow provider (repeatable); replaces allowed_providers list",
    )
    cbud.add_argument(
        "--block-provider",
        action="append",
        default=None,
        dest="block_providers",
        help="L3 scope: block provider (repeatable)",
    )
    cbud.add_argument(
        "--allow-intent",
        action="append",
        default=None,
        dest="allow_intents",
        help="L3 scope: allow intent e.g. free_llm,search (repeatable)",
    )
    cbud.add_argument(
        "--block-intent",
        action="append",
        default=None,
        dest="block_intents",
        help="L3 scope: block intent (repeatable)",
    )
    cbud.add_argument(
        "--allow-op",
        action="append",
        default=None,
        dest="allow_ops",
        help="L3 scope: allow op e.g. chat,search (repeatable)",
    )
    cbud.add_argument(
        "--block-op",
        action="append",
        default=None,
        dest="block_ops",
        help="L3 scope: block op (repeatable)",
    )
    cbud.add_argument(
        "--clear-scopes",
        action="store_true",
        help="remove all allowed_*/blocked_* lists for this consumer",
    )
    cbud.add_argument(
        "--clear",
        action="store_true",
        help="remove envelope for this consumer (fall back to _default)",
    )

    padd = sub.add_parser("provider-add", help="Scaffold distill JSON for a new provider")
    padd.add_argument("id", help="provider id (e.g. azure_openai)")
    padd.add_argument("--title", default="", help="display title")
    padd.add_argument("--base-url", default="", dest="base_url")
    padd.add_argument(
        "--auth",
        default="bearer",
        choices=["bearer", "header_token", "xi_api_key"],
    )
    padd.add_argument("--env-key", default="", dest="env_key", help="e.g. AZURE_OPENAI_API_KEY")
    padd.add_argument(
        "--high-risk",
        action="store_true",
        help="mark high_risk (must enable explicitly + tight $ caps)",
    )

    risk = sub.add_parser("high-risk", help="List / set high_risk_providers in keys_app.json")
    risk.add_argument("action", choices=["list", "add", "remove"])
    risk.add_argument("provider", nargs="?", default="")

    doc = sub.add_parser("doctor", help="Self-diagnose install/config (first step after setup)")
    doc.add_argument("--live", action="store_true", help="include live provider diagnose")
    doc.add_argument("--json", action="store_true", help="machine-readable output")

    sub.add_parser(
        "suggest",
        help="Propose routing/budget tweaks from ledger (never auto-applies)",
    )

    alrt = sub.add_parser(
        "alert",
        help="Webhook alerts: test delivery or list event catalog",
    )
    alrt.add_argument(
        "action",
        choices=["test", "events"],
        help="test | events",
    )
    alrt.add_argument(
        "--message",
        default="tollgate alert test",
        help="message for alert test",
    )

    snap = sub.add_parser(
        "snapshot",
        help="Export/import desk ops state (portable USB migration)",
    )
    snap.add_argument(
        "action",
        choices=["export", "import", "info"],
        help="export | import | info",
    )
    snap.add_argument(
        "path",
        nargs="?",
        default="",
        help="archive path (.tgz)",
    )
    snap.add_argument(
        "-o",
        "--output",
        default="",
        help="export destination (default: tollgate-snapshot-<day>.tgz)",
    )
    snap.add_argument(
        "--include-secrets",
        action="store_true",
        help="export Key.txt / .env (sensitive — off by default)",
    )
    snap.add_argument(
        "--no-audit",
        action="store_true",
        help="omit audit.jsonl from export",
    )
    snap.add_argument(
        "--replace",
        action="store_true",
        help="import: overwrite existing files (default merges keys_app only)",
    )
    snap.add_argument(
        "--dry-run",
        action="store_true",
        help="import: show plan without writing",
    )

    rep = sub.add_parser(
        "report",
        help="Daily operator report — Protect · Route · Prove evidence",
    )
    rep.add_argument(
        "--format",
        choices=["json", "md", "markdown"],
        default="md",
        dest="report_format",
        help="md (default) or json",
    )
    rep.add_argument(
        "-o",
        "--output",
        default="",
        help="write to file (optional)",
    )

    aud = sub.add_parser(
        "audit",
        help="Query audit trail — who was denied and why (ops only)",
    )
    aud.add_argument(
        "--event",
        default="",
        help="filter event (admit_deny, usage, …)",
    )
    aud.add_argument("--consumer", default="", help="filter consumer/agent id")
    aud.add_argument("--provider", default="", help="filter provider id")
    aud.add_argument("--limit", type=int, default=30, help="max rows (default 30)")
    aud.add_argument(
        "--summary",
        action="store_true",
        help="aggregates: top deny reasons + by event/consumer",
    )
    aud.add_argument("--json", action="store_true", help="machine-readable (default)")

    srch = sub.add_parser(
        "search",
        help="Search repo modules / docs / HTTP / CLI (find code without guessing paths)",
    )
    srch.add_argument(
        "query",
        nargs="*",
        default=[],
        help="search terms (e.g. circuit breaker); omit with --map",
    )
    srch.add_argument(
        "--kind",
        action="append",
        dest="kinds",
        default=None,
        help="filter: concept module doc http cli config script (repeatable)",
    )
    srch.add_argument("--limit", type=int, default=15, help="max hits (default 15)")
    srch.add_argument("--json", action="store_true", help="machine-readable output")
    srch.add_argument(
        "--map",
        action="store_true",
        help="print full repo map markdown (docs/MAP.md body)",
    )

    args = p.parse_args(argv)

    if args.cmd == "mcp" or (args.cmd is None and len(sys.argv) == 1):
        from tollgate.mcp import main as mcp_main

        mcp_main()
        return

    if args.cmd == "serve":
        import os

        import uvicorn

        from tollgate.app_config import load_config
        from tollgate.config_validate import assert_config_or_raise
        from tollgate.paths import pin_data_home_env

        pin_data_home_env()
        cfg = load_config(force=True)
        strict = (os.environ.get("TOLLGATE_STRICT_CONFIG") or "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        try:
            warns = assert_config_or_raise(cfg, strict=strict)
            for w in warns:
                print(f"[tollgate] config: {w}", file=sys.stderr)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            raise SystemExit(2) from e
        host = os.environ.get("HOST", "127.0.0.1")
        port = int(os.environ.get("PORT", "8787"))
        uvicorn.run("tollgate.server_v1:app", host=host, port=port, reload=False)
        return

    if args.cmd == "doctor":
        from tollgate.doctor import format_doctor_text, run_doctor

        report = run_doctor(live=bool(args.live))
        if args.json:
            print(json.dumps(report, indent=2, default=str))
        else:
            print(format_doctor_text(report))
        raise SystemExit(0 if report.get("ok") else 1)

    if args.cmd == "suggest":
        from tollgate.paths import pin_data_home_env
        from tollgate.suggest import routing_suggestions

        pin_data_home_env()
        print(json.dumps(routing_suggestions(), indent=2, default=str))
        return

    if args.cmd == "search":
        from tollgate.repo_search import format_search_text, map_markdown, search

        if args.map:
            print(map_markdown())
            return
        q = " ".join(args.query or []).strip()
        if not q:
            print(
                "usage: tollgate search <query> [--kind module] [--json]\n"
                "       tollgate search --map\n"
                "examples: tollgate search circuit breaker\n"
                "          tollgate search budget --kind concept\n"
                "map: docs/MAP.md",
                file=sys.stderr,
            )
            raise SystemExit(2)
        result = search(q, limit=int(args.limit), kinds=args.kinds)
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(format_search_text(result))
        raise SystemExit(0 if result.get("hits") else 1)

    if args.cmd == "audit":
        from tollgate.audit_log import audit_summary, query_audit
        from tollgate.paths import pin_data_home_env

        pin_data_home_env()
        if args.summary:
            out = audit_summary()
            print(json.dumps(out, indent=2, default=str))
            return
        out = query_audit(
            limit=int(args.limit),
            event=args.event,
            consumer=args.consumer,
            provider=args.provider,
        )
        if args.json or True:
            # always JSON for machine + human-friendly structure
            print(json.dumps(out, indent=2, default=str))
        return

    if args.cmd == "report":
        from pathlib import Path

        from tollgate.paths import pin_data_home_env
        from tollgate.report import build_report, format_report_markdown

        pin_data_home_env()
        fmt = (args.report_format or "md").lower()
        if fmt in ("md", "markdown"):
            text = format_report_markdown()
        else:
            text = json.dumps(build_report(), indent=2, default=str)
        out_path = (args.output or "").strip()
        if out_path:
            Path(out_path).expanduser().write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")
            print(f"wrote {out_path}", file=sys.stderr)
        print(text)
        return

    if args.cmd == "alert":
        from tollgate.alerts import event_catalog, test_webhook
        from tollgate.paths import pin_data_home_env

        pin_data_home_env()
        if args.action == "events":
            print(json.dumps(event_catalog(), indent=2, default=str))
            return
        out = test_webhook(message=args.message)
        print(json.dumps(out, indent=2, default=str))
        raise SystemExit(0 if out.get("ok") else 1)

    if args.cmd == "snapshot":
        from datetime import date
        from pathlib import Path

        from tollgate.paths import pin_data_home_env
        from tollgate.snapshot import export_snapshot, import_snapshot, snapshot_info

        pin_data_home_env()
        action = args.action
        if action == "export":
            out = (args.output or args.path or "").strip()
            if not out:
                out = f"tollgate-snapshot-{date.today().isoformat()}.tgz"
            result = export_snapshot(
                out,
                include_secrets=bool(args.include_secrets),
                include_audit=not bool(args.no_audit),
            )
            print(json.dumps(result, indent=2, default=str))
            raise SystemExit(0 if result.get("ok") else 1)
        path = (args.path or args.output or "").strip()
        if not path:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "path required: tollgate snapshot import <file.tgz>",
                    }
                )
            )
            raise SystemExit(2)
        if action == "info":
            print(json.dumps(snapshot_info(path), indent=2, default=str))
            return
        result = import_snapshot(
            path,
            dry_run=bool(args.dry_run),
            replace=bool(args.replace),
        )
        print(json.dumps(result, indent=2, default=str))
        raise SystemExit(0 if result.get("ok") else 1)

    if args.cmd == "health":
        from tollgate import get_keys_service
        from tollgate.consumers import auth_status
        from tollgate.cost import high_risk_ids
        from tollgate.paths import path_snapshot, pin_data_home_env

        pin_data_home_env()
        print(
            json.dumps(
                {
                    "ok": True,
                    "portable": path_snapshot(),
                    "auth": auth_status(),
                    "high_risk_providers": sorted(high_risk_ids()),
                    "app": get_keys_service().app_status(),
                },
                indent=2,
                default=str,
            )
        )
        return

    if args.cmd == "control":
        from tollgate.control_plane import control_snapshot
        from tollgate.paths import pin_data_home_env

        pin_data_home_env()
        print(json.dumps(control_snapshot(), indent=2, default=str))
        return

    if args.cmd == "resilience":
        from tollgate.paths import pin_data_home_env
        from tollgate.resilience import resilience_score

        pin_data_home_env()
        print(json.dumps(resilience_score(), indent=2, default=str))
        return

    if args.cmd == "chaos":
        from tollgate.chaos import run_failover_test, start_chaos, status, stop_chaos
        from tollgate.paths import pin_data_home_env

        pin_data_home_env()

        def _parse_dur(s: str) -> float:
            s = (s or "5m").strip().lower()
            if s.endswith("ms"):
                return max(0.001, float(s[:-2]) / 1000.0)
            if s.endswith("s"):
                return max(1.0, float(s[:-1]))
            if s.endswith("m"):
                return max(1.0, float(s[:-1]) * 60.0)
            if s.endswith("h"):
                return max(1.0, float(s[:-1]) * 3600.0)
            return max(1.0, float(s))

        if args.action == "status":
            print(json.dumps(status(), indent=2, default=str))
            return
        if args.action == "stop":
            print(
                json.dumps(
                    stop_chaos(args.provider, all_injects=bool(args.all)),
                    indent=2,
                    default=str,
                )
            )
            return
        if args.action == "start":
            if not args.provider:
                print(json.dumps({"ok": False, "error": "provider required"}))
                raise SystemExit(1)
            print(
                json.dumps(
                    start_chaos(
                        args.provider,
                        duration_s=_parse_dur(args.duration),
                        reason="cli",
                    ),
                    indent=2,
                    default=str,
                )
            )
            return
        if args.action == "test":
            if not args.provider:
                print(json.dumps({"ok": False, "error": "provider required"}))
                raise SystemExit(1)
            rep = run_failover_test(
                args.provider,
                intent=args.intent,
                requests=int(args.requests),
                duration_s=_parse_dur(args.duration),
                live_chat=bool(args.live_chat),
            )
            print(json.dumps(rep, indent=2, default=str))
            raise SystemExit(0 if rep.get("survived") or rep.get("ok") else 1)
        return

    if args.cmd == "paths":
        from tollgate.paths import path_snapshot, pin_data_home_env

        pin_data_home_env()
        print(json.dumps(path_snapshot(), indent=2))
        return

    if args.cmd == "consumer-add":
        from tollgate.consumers import add_consumer
        from tollgate.paths import pin_data_home_env

        pin_data_home_env()
        out = add_consumer(
            args.id,
            secret=args.secret or None,
            admin=bool(args.admin),
            label=args.label or args.id,
        )
        print(json.dumps(out, indent=2))
        if out.get("ok"):
            print(
                f"\nUse header: X-Consumer-Key: {out['id']}:{out['secret']}",
                file=sys.stderr,
            )
        return

    if args.cmd == "consumer-budget":
        from tollgate.app_config import load_config, save_config
        from tollgate.limits import check_consumer_limits, consumer_envelope
        from tollgate.paths import pin_data_home_env
        from tollgate.usage_ledger import consumer_usage, load_usage

        pin_data_home_env()
        if args.list or not args.id:
            cfg = load_config(force=True)
            envs = dict(cfg.get("consumer_envelopes") or {})
            day = load_usage()
            used = day.get("consumers") or {}
            rows = []
            ids = set(envs.keys()) | set(used.keys())
            for cid in sorted(ids):
                if cid.startswith("_") and cid != "_default":
                    continue
                rows.append(
                    {
                        "id": cid,
                        "envelope": envs.get(cid) or {},
                        "usage": used.get(cid) or {},
                        "limits": check_consumer_limits(cid) if cid != "_default" else None,
                    }
                )
            print(json.dumps({"ok": True, "envelopes": rows, "raw": envs}, indent=2, default=str))
            return
        cid = (args.id or "").strip()[:64]
        if not cid or cid == "anonymous":
            print(json.dumps({"ok": False, "error": "invalid consumer id"}))
            raise SystemExit(1)
        cfg = load_config(force=True)
        envs = dict(cfg.get("consumer_envelopes") or {})
        if args.clear:
            envs.pop(cid, None)
            cfg["consumer_envelopes"] = envs
            save_config(cfg)
            print(json.dumps({"ok": True, "id": cid, "cleared": True}, indent=2))
            return
        block = dict(envs.get(cid) or {})
        if args.max_calls_day is not None:
            block["max_calls_day"] = int(args.max_calls_day)
        if args.max_tokens_day is not None:
            block["max_tokens_day"] = int(args.max_tokens_day)
        if args.max_usd_day is not None:
            block["max_usd_day"] = float(args.max_usd_day)
        if args.max_usd_request is not None:
            block["max_usd_request"] = float(args.max_usd_request)
        if args.max_usd_hour is not None:
            block["max_usd_hour"] = float(args.max_usd_hour)
        if args.max_requests_minute is not None:
            block["max_requests_minute"] = int(args.max_requests_minute)
        if args.max_tokens_request is not None:
            block["max_tokens_request"] = int(args.max_tokens_request)
        if args.max_tool_calls is not None:
            block["max_tool_calls"] = int(args.max_tool_calls)
        # L3 scopes
        if getattr(args, "clear_scopes", False):
            for k in (
                "allowed_providers",
                "blocked_providers",
                "allowed_ops",
                "blocked_ops",
                "allowed_intents",
                "blocked_intents",
            ):
                block.pop(k, None)
        if args.allow_providers is not None:
            block["allowed_providers"] = [
                str(x).strip().lower() for x in args.allow_providers if str(x).strip()
            ]
        if args.block_providers is not None:
            block["blocked_providers"] = [
                str(x).strip().lower() for x in args.block_providers if str(x).strip()
            ]
        if args.allow_intents is not None:
            block["allowed_intents"] = [
                str(x).strip().lower() for x in args.allow_intents if str(x).strip()
            ]
        if args.block_intents is not None:
            block["blocked_intents"] = [
                str(x).strip().lower() for x in args.block_intents if str(x).strip()
            ]
        if args.allow_ops is not None:
            block["allowed_ops"] = [
                str(x).strip().lower() for x in args.allow_ops if str(x).strip()
            ]
        if args.block_ops is not None:
            block["blocked_ops"] = [
                str(x).strip().lower() for x in args.block_ops if str(x).strip()
            ]
        if not block:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": (
                            "pass --max-usd-day / --allow-provider / "
                            "--max-requests-minute / … or --clear"
                        ),
                    }
                )
            )
            raise SystemExit(1)
        envs[cid] = block
        cfg["consumer_envelopes"] = envs
        save_config(cfg)
        print(
            json.dumps(
                {
                    "ok": True,
                    "id": cid,
                    "envelope": consumer_envelope(cid),
                    "usage": consumer_usage(cid),
                    "limits": check_consumer_limits(cid),
                },
                indent=2,
                default=str,
            )
        )
        return

    if args.cmd == "provider-add":
        from tollgate.paths import pin_data_home_env
        from tollgate.provider_scaffold import scaffold_provider

        pin_data_home_env()
        out = scaffold_provider(
            args.id,
            title=args.title,
            base_url=args.base_url,
            auth=args.auth,
            env_key=args.env_key,
            high_risk=bool(args.high_risk),
        )
        print(json.dumps(out, indent=2, default=str))
        return

    if args.cmd == "high-risk":
        from tollgate.app_config import load_config, save_config
        from tollgate.cost import high_risk_ids
        from tollgate.paths import pin_data_home_env

        pin_data_home_env()
        if args.action == "list":
            print(json.dumps({"high_risk_providers": sorted(high_risk_ids())}, indent=2))
            return
        pid = (args.provider or "").strip().lower()
        if not pid:
            print(json.dumps({"ok": False, "error": "provider id required"}))
            return
        cfg = load_config(force=True)
        guard = dict(cfg.get("cost_guard") or {})
        lst = [str(x).lower() for x in (guard.get("high_risk_providers") or [])]
        if args.action == "add" and pid not in lst:
            lst.append(pid)
        if args.action == "remove":
            lst = [x for x in lst if x != pid]
        guard["high_risk_providers"] = lst
        cfg["cost_guard"] = guard
        save_config(cfg)
        # ensure provider block exists disabled if high-risk add
        if args.action == "add":
            provs = dict(cfg.get("providers") or {})
            block = dict(provs.get(pid) or {})
            block.setdefault("enabled", False)
            block.setdefault("high_risk", True)
            block.setdefault("max_usd_day", 1.0)
            block.setdefault("max_calls_day", 20)
            provs[pid] = block
            cfg["providers"] = provs
            save_config(cfg)
        print(json.dumps({"ok": True, "high_risk_providers": lst, "action": args.action, "provider": pid}, indent=2))
        return

    p.print_help()


if __name__ == "__main__":
    main()
