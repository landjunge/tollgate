"""tollgate CLI entry."""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="tollgate", description="Tollgate — API admission gateway")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("serve", help="Run HTTP server (uvicorn)")
    sub.add_parser("mcp", help="Run MCP stdio server")
    sub.add_parser("health", help="Print local health JSON (paths + auth mode)")
    sub.add_parser("paths", help="Print portable path snapshot")

    cadd = sub.add_parser("consumer-add", help="Add HTTP consumer (id:secret)")
    cadd.add_argument("id", help="consumer id (e.g. n8n, gnom)")
    cadd.add_argument("--admin", action="store_true", help="allow /v1/config")
    cadd.add_argument("--secret", default="", help="optional fixed secret")
    cadd.add_argument("--label", default="", help="display label")

    cbud = sub.add_parser(
        "consumer-budget",
        help="Set / list per-consumer day envelopes (keys_app.json consumer_envelopes)",
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
        if not block:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "pass --max-usd-day / --max-calls-day / --max-tokens-day or --clear",
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
