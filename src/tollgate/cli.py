"""tollgate CLI entry."""

from __future__ import annotations

import argparse
import json
import sys


def _format_help(topic: str = "") -> str:
    """Human help text (mirrors docs/HILFE.md + USER_GUIDE.md)."""
    t = (topic or "").strip().lower()
    topics = {
        "start": """
# Start / install

  python3 -m venv .venv && .venv/bin/pip install -e .
  export TOLLGATE_HOME=$HOME/.tollgate
  tollgate serve                    # http://127.0.0.1:8787
  ./scripts/ten-minute.sh           # cold 10-minute path
  ./scripts/desk-ready.sh           # doctor + server + smoke

  Docker:  docker compose up -d --build
  UI:      http://127.0.0.1:8787/dashboard
  API:     http://127.0.0.1:8787/docs

  Keys (optional for Protect demo): $TOLLGATE_HOME/User/Key.txt
  Handbook: docs/HILFE.md · docs/USER_GUIDE.md · docs/TEN_MINUTE.md
""",
        "protect": """
# Protect — agent must never go out of control

  tollgate consumer-budget support-agent \\
    --max-usd-day 2 --max-usd-request 0.5 \\
    --max-tool-calls 20 --max-requests-minute 50

  tollgate consumer-budget support-agent \\
    --allow-provider opencode_zen --allow-intent free_llm --allow-op chat

  # Tool-loop Aha (no spend required)
  curl -s http://127.0.0.1:8787/v1/invoke \\
    -H 'Content-Type: application/json' \\
    -H 'X-Consumer-Key: support-agent' \\
    -d '{"provider":"opencode_zen","op":"chat","tool_calls_est":99,"arguments":{"message":"x"}}'

  # OpenAI drop-in: send tool_calls_est or tool history
  #   body:  "tool_calls_est": 12
  #   header: X-Tollgate-Tool-Calls-Est: 12
  #   auto:  count role=tool + assistant.tool_calls in messages
  # See docs/OPENAI.md

  tollgate freeze --reason "incident"   # kill switch
  tollgate unfreeze
  Dashboard: Overview → "Test tool-loop block"
""",
        "route": """
# Route — health-aware failover

  curl -s http://127.0.0.1:8787/v1/route \\
    -H 'Content-Type: application/json' -H 'X-Consumer-Key: desk' \\
    -d '{"intent":"free_llm","tokens_est":1000}'

  tollgate circuits list
  tollgate circuits reset deepseek
  tollgate circuits reset --all
""",
        "prove": """
# Prove — chaos / resilience / certificate

  tollgate chaos test opencode_zen --requests 10
  tollgate resilience
  tollgate certificate --application "Support Agent"
  tollgate demo                     # Protect + Prove live script

  Dashboard → Prove → Run test

  NOT_RUN / failed chaos is normal when:
    · only one provider in free_llm chain
    · missing keys (tollgate doctor)
  Protect (budgets / max_tool_calls) can PASS without chaos.
  Next: enable 2nd provider → Key.txt → chaos test → certificate
""",
        "ui": """
# Control Room WebUI

  http://127.0.0.1:8787/dashboard

  Overview  — safe? broken? expensive? what to do?
  Agents    — budgets, edit protection, loop test
  Providers — health / latency / cost
  Prove     — chaos test + certificate
  Audit     — who was blocked

  Badge: PROTECTED | ATTENTION | FROZEN
  Setup wizard: first protected lane without CLI
""",
        "api": """
# HTTP surfaces (base http://127.0.0.1:8787)

  GET  /dashboard /docs /metrics
  GET  /v1/health /v1/control /v1/status /v1/certificate
  GET  /v1/audit /v1/budget /v1/resilience /v1/chaos
  POST /v1/route /v1/invoke /v1/chat/completions /v1/messages
  POST /v1/config /v1/chaos/test /v1/freeze /v1/circuits/reset

  OpenAI drop-in:
    export OPENAI_BASE_URL=http://127.0.0.1:8787/v1
    export OPENAI_API_KEY=support-agent

  Full OpenAPI: /docs  ·  Handbooks: docs/HILFE.md docs/USER_GUIDE.md
""",
        "ops": """
# Operations

  tollgate doctor
  tollgate status
  tollgate report --format md
  tollgate audit --event admit_deny --limit 20
  tollgate alert test
  tollgate snapshot export -o desk.tgz
  tollgate search circuit breaker

  Webhook: TOLLGATE_ALERT_WEBHOOK or cost_guard.alert_webhook_url
  Metrics auth: consumer key | TOLLGATE_METRICS_TOKEN | PUBLIC=1
  Portable: docs/PORTABLE.md · docs/OPERATIONS.md
""",
        "troubleshoot": """
# Troubleshooting

  Server won't start     → tollgate doctor · free port 8787 · Python ≥ 3.11
  401 Unauthorized       → auth mode needs id:secret · consumer-add
  Always blocked         → envelope / freeze status / scopes
  Chaos failed / NOT_RUN → ≥2 providers in free_llm · keys · doctor
  Loop never blocks      → send tool_calls_est (body/header) or tool history
  Stale dashboard        → hard refresh · check /v1/health version
  Wrong data home        → tollgate paths · echo $TOLLGATE_HOME
  Metrics 401            → token / consumer / TOLLGATE_METRICS_PUBLIC=1

  Log (desk): /tmp/tollgate-desk.log
  Docs: docs/OPENAI.md (tool_calls_est) · docs/FAQ.md
""",
        "commands": """
# All CLI commands

  serve mcp health control resilience chaos paths
  consumer-add consumer-budget provider-add high-risk
  doctor suggest status certificate demo
  freeze unfreeze circuits alert snapshot
  report audit search help

  Examples:
    tollgate consumer-budget support-agent --max-usd-day 2 --max-tool-calls 20
    tollgate chaos test opencode_zen --requests 8
    tollgate certificate
    tollgate demo --skip-chaos
""",
        "env": """
# Environment variables

  TOLLGATE_HOME              data root (contains User/)
  GNOM_WS                    fallback data root
  TOLLGATE_CONFIG            absolute keys_app.json override
  GNOM_KEYS_CONFIG           alias for config override
  TOLLGATE_PORTABLE=1        portable path resolution
  TOLLGATE_REQUIRE_AUTH=1    force auth mode (id:secret)
  TOLLGATE_CONSUMERS         consumers.json path override
  TOLLGATE_FROZEN=1          kill switch (also TOLLGATE_ADMISSION_FROZEN)
  TOLLGATE_ALERT_WEBHOOK     alert URL (or cost_guard.alert_webhook_url)
  TOLLGATE_METRICS_TOKEN     Bearer for /metrics
  TOLLGATE_METRICS_PUBLIC=1  open /metrics (lab only)
  TOLLGATE_STRICT_CONFIG=1   hard-fail invalid config
  TOLLGATE_URL               client base (default http://127.0.0.1:8787)
  TOLLGATE_CONSUMER          client default lane
  HOST / PORT                tollgate serve bind (127.0.0.1 / 8787)

  Provider keys: $TOLLGATE_HOME/User/Key.txt or process env
  Handbook: docs/HILFE.md §18 · docs/USER_GUIDE.md §16
""",
        "config": """
# Config (keys_app.json)

  Path: $TOLLGATE_HOME/User/keys_app.json
  Defaults: src/tollgate/app_config.py DEFAULT_CONFIG

  Main blocks:
    cost_guard          global $ cap, high_risk, soft_warn, webhook
    consumer_envelopes  per-lane budgets + scopes + tool_calls
    providers.<id>      enabled, max_usd_day, …
    circuits            breaker thresholds / cooldown
    reliability         Prove targets
    admission           freeze flags

  CLI:
    tollgate consumer-budget …     # envelopes
    tollgate high-risk list|add
    tollgate freeze / unfreeze

  HTTP:
    GET  /v1/config
    POST /v1/config   # deep-merge; invalid → 400 not written

  Detail: docs/COST_LIMITS.md · docs/HILFE.md §19
""",
        "faq": """
# FAQ (short)

  Keys for demo?     No for Protect tool-loop; yes for real chat/chaos
  vs LiteLLM?        LiteLLM routes models; Tollgate stops agents + proves DR
  Always blocked?    freeze · envelope · scope · audit --event admit_deny
  tool_calls_est?    Client must send loop depth for max_tool_calls
  Unlimited budget?  Set dimension to 0 (other dims still apply)
  Multi-worker?      Share TOLLGATE_HOME (see docs/STABILITY.md)
  Find code?         tollgate search <q> · tollgate search --map
  Full FAQ:          docs/FAQ.md · DE handbook docs/HILFE.md
""",
    }
    if t in topics:
        return topics[t].strip() + "\n"
    if t:
        return (
            f"Unknown topic: {t!r}\n\n"
            + _format_help("")
        )
    return """
Tollgate — safety layer for AI agents (Protect · Route · Prove)

  “My AI agent must never go out of control.”

Quick start
  ./scripts/ten-minute.sh
  tollgate serve
  open http://127.0.0.1:8787/dashboard

Help topics
  tollgate help start          install & cold path
  tollgate help protect        budgets, loops, freeze, scopes
  tollgate help route          failover & circuits
  tollgate help prove          chaos, resilience, certificate
  tollgate help ui             Control Room WebUI
  tollgate help api            HTTP / OpenAI drop-in
  tollgate help ops            doctor, audit, snapshot, alerts
  tollgate help troubleshoot   common failures
  tollgate help commands       full command list
  tollgate help env            environment variables
  tollgate help config         keys_app.json recipes
  tollgate help faq            short FAQ

Handbooks
  docs/HILFE.md        German detailed help
  docs/USER_GUIDE.md   English user guide
  docs/FAQ.md          FAQ
  docs/TEN_MINUTE.md   10-minute stranger test
  docs/DEMO.md         killer demo script
  docs/PRODUCT.md      positioning
  Website              https://landjunge.github.io/tollgate/

Repo search
  tollgate search <query>
  tollgate search --map
""".strip() + "\n"


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        prog="tollgate",
        description=(
            "Tollgate — safety layer for AI agents (Protect · Route · Prove). "
            "Try: tollgate help"
        ),
    )
    sub = p.add_subparsers(dest="cmd")
    help_p = sub.add_parser("help", help="User help — topics and handbook links")
    help_p.add_argument(
        "topic",
        nargs="?",
        default="",
        help="start|protect|route|prove|ui|api|ops|troubleshoot|commands|env|config|faq",
    )

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

    st = sub.add_parser(
        "status",
        help="Compact desk status (freeze · resilience · spend · attention)",
    )
    st.add_argument(
        "--json",
        action="store_true",
        help="machine-readable JSON (default is human text)",
    )

    cert = sub.add_parser(
        "certificate",
        help="AI Reliability Report scorecard (PASS/FAIL for Protect·Route·Prove)",
    )
    cert.add_argument(
        "--application",
        default="",
        help="label e.g. Customer Support Agent",
    )
    cert.add_argument("--json", action="store_true", help="JSON instead of text card")

    dem = sub.add_parser(
        "demo",
        help="Killer demo: agent tool-loop block + optional chaos DR proof",
    )
    dem.add_argument(
        "--skip-chaos",
        action="store_true",
        help="only Protect Aha (no chaos test)",
    )
    dem.add_argument(
        "--consumer",
        default="support-agent",
        help="agent lane id (default support-agent)",
    )
    dem.add_argument(
        "--provider",
        default="opencode_zen",
        help="provider for chaos / invoke attempt (default opencode_zen)",
    )

    frz = sub.add_parser(
        "freeze",
        help="Emergency kill switch — deny all billable admission",
    )
    frz.add_argument(
        "action",
        nargs="?",
        default="on",
        choices=["on", "off", "status", "unfreeze"],
        help="on (default) | off/unfreeze | status",
    )
    frz.add_argument(
        "--reason",
        default="",
        help="why freeze (audit + webhook)",
    )
    sub.add_parser("unfreeze", help="Alias for: freeze off")

    circ = sub.add_parser(
        "circuits",
        help="List or reset circuit breakers",
    )
    circ.add_argument(
        "action",
        choices=["list", "reset", "status"],
        help="list | reset | status",
    )
    circ.add_argument(
        "provider",
        nargs="?",
        default="",
        help="provider id for reset (omit with --all)",
    )
    circ.add_argument(
        "--all",
        action="store_true",
        dest="all_circuits",
        help="reset every circuit",
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

    if args.cmd == "help":
        print(_format_help(getattr(args, "topic", "") or ""))
        return

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
        host = (os.environ.get("HOST") or "127.0.0.1").strip() or "127.0.0.1"
        port = int(os.environ.get("PORT", "8787"))
        try:
            from tollgate.consumers import auth_required

            if not auth_required() and host in ("0.0.0.0", "::", "[::]", "*"):
                print(
                    "[tollgate] WARNING: open auth mode on public bind "
                    f"{host}:{port} — use HOST=127.0.0.1 or configure consumers.",
                    file=sys.stderr,
                )
            elif not auth_required():
                print(
                    f"[tollgate] open mode (local desk) · dashboard "
                    f"http://{host}:{port}/dashboard",
                    file=sys.stderr,
                )
            else:
                print(
                    f"[tollgate] auth mode · http://{host}:{port}/dashboard",
                    file=sys.stderr,
                )
        except Exception:  # noqa: BLE001
            pass
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

    if args.cmd == "status":
        from tollgate.paths import pin_data_home_env
        from tollgate.status import desk_status, format_status_text

        pin_data_home_env()
        if args.json:
            print(json.dumps(desk_status(), indent=2, default=str))
        else:
            print(format_status_text())
        return

    if args.cmd == "certificate":
        from tollgate.certificate import build_certificate, format_certificate_text
        from tollgate.paths import pin_data_home_env

        pin_data_home_env()
        cert_data = build_certificate(application=args.application or "")
        if args.json:
            print(json.dumps(cert_data, indent=2, default=str))
        else:
            print(format_certificate_text(cert_data))
        # non-zero if protect hard-fails
        overall = cert_data.get("overall")
        raise SystemExit(1 if overall in ("NEEDS_PROTECT", "FROZEN") else 0)

    if args.cmd == "demo":
        import os
        import subprocess
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        script = root / "scripts" / "demo-agent-safety.sh"
        if not script.is_file():
            # installed wheel: fall back to in-process mini demo
            from tollgate.paths import pin_data_home_env

            pin_data_home_env()
            print(
                "demo script not found — run from repo checkout:\n"
                "  ./scripts/demo-agent-safety.sh\n"
                "or: docs/DEMO.md",
                file=sys.stderr,
            )
            raise SystemExit(2)
        env = os.environ.copy()
        env["DEMO_CONSUMER"] = str(args.consumer or "support-agent")
        env["DEMO_CHAOS_PROVIDER"] = str(args.provider or "opencode_zen")
        if args.skip_chaos:
            env["SKIP_CHAOS"] = "1"
        raise SystemExit(subprocess.call(["bash", str(script)], env=env))

    if args.cmd in ("freeze", "unfreeze"):
        from tollgate.freeze import freeze_status, set_frozen
        from tollgate.paths import pin_data_home_env

        pin_data_home_env()
        if args.cmd == "unfreeze":
            out = set_frozen(False, reason="", by="cli")
            print(json.dumps(out, indent=2, default=str))
            raise SystemExit(0)
        act = (getattr(args, "action", None) or "on").lower()
        if act == "status":
            print(json.dumps(freeze_status(), indent=2, default=str))
            return
        if act in ("off", "unfreeze"):
            out = set_frozen(False, reason=args.reason or "", by="cli")
            print(json.dumps(out, indent=2, default=str))
            raise SystemExit(0)
        out = set_frozen(
            True,
            reason=args.reason or "manual freeze via CLI",
            by="cli",
        )
        print(json.dumps(out, indent=2, default=str))
        raise SystemExit(0)

    if args.cmd == "circuits":
        from tollgate.gateway.circuit import get_circuits, reset_circuits
        from tollgate.paths import pin_data_home_env

        pin_data_home_env()
        if args.action in ("list", "status"):
            rows = get_circuits().snapshot()
            print(
                json.dumps(
                    {"ok": True, "count": len(rows), "circuits": rows},
                    indent=2,
                    default=str,
                )
            )
            return
        # reset
        if not args.provider and not args.all_circuits:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "provider id required, or pass --all",
                    }
                )
            )
            raise SystemExit(2)
        out = reset_circuits(
            args.provider or "",
            all_circuits=bool(args.all_circuits),
        )
        print(json.dumps(out, indent=2, default=str))
        return

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
