"""
Repo search — make Tollgate source/docs findable without guessing paths.

CLI:  tollgate search circuit breaker
      tollgate search budget --kind module
      tollgate search /v1/messages --json

Scans (in order of ranking boost):
  1. Curated concept index (product vocabulary → paths)
  2. Module docstrings under src/tollgate/
  3. Docs headings + body (docs/**/*.md)
  4. HTTP routes from server_v1.py
  5. CLI subcommands (static table kept in sync with cli.py)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


# ── paths ────────────────────────────────────────────────────────────


def package_dir() -> Path:
    return Path(__file__).resolve().parent


def repo_root() -> Path | None:
    """Editable install: …/tollgate/src/tollgate → repo root. Else None."""
    pkg = package_dir()
    # …/src/tollgate
    if pkg.parent.name == "src":
        root = pkg.parent.parent
        if (root / "pyproject.toml").is_file() or (root / "docs").is_dir():
            return root
    return None


def docs_dir() -> Path | None:
    root = repo_root()
    if root and (root / "docs").is_dir():
        return root / "docs"
    # wheel: no docs shipped — fall back to none
    return None


# ── curated concept index (product vocabulary) ───────────────────────

# keywords (space-split) → hits people actually type
CONCEPTS: list[dict[str, Any]] = [
    {
        "id": "protect-route-prove",
        "title": "Protect · Route · Prove (product pillars)",
        "path": "docs/PRODUCT.md",
        "summary": "Safety layer for AI agents — not an API gateway catalog.",
        "keywords": "product protect route prove wedge reliability control plane agent safety",
    },
    {
        "id": "demo-killer",
        "title": "Killer demo — agent loop + DR proof",
        "path": "docs/DEMO.md",
        "summary": "My AI agent must never go out of control; tool_call block + chaos survive.",
        "keywords": "demo agent loop tool_calls max_tool_calls chaos prove aha support-agent",
    },
    {
        "id": "agent-protection",
        "title": "Agent protection (loop / $ / RPM hard stops)",
        "path": "src/tollgate/agent_guard.py",
        "summary": "max_usd_request/hour, max_requests_minute, max_tool_calls, max_tokens_request.",
        "keywords": "agent loop runaway budget rpm tool_calls envelope protection guard",
    },
    {
        "id": "consumer-envelopes",
        "title": "Consumer day envelopes",
        "path": "src/tollgate/limits.py",
        "summary": "Per-consumer max_usd_day / calls / tokens; _default fallback.",
        "keywords": "consumer envelope budget day n8n gnom consumer-budget",
    },
    {
        "id": "admission",
        "title": "L4 Admission (fail-closed)",
        "path": "src/tollgate/gateway/admit.py",
        "summary": "Hard deny before HTTP; cost velocity, high-risk, soft warn.",
        "keywords": "admit admission deny fail-closed preflight budget hard stop",
    },
    {
        "id": "circuit",
        "title": "Circuit breaker + cooldown jitter",
        "path": "src/tollgate/gateway/circuit.py",
        "summary": "Per (provider, model, key_ref); sticky hard cooldown; optional jitter.",
        "keywords": "circuit breaker cooldown jitter open half-open thundering herd",
    },
    {
        "id": "router",
        "title": "Health-aware router",
        "path": "src/tollgate/router.py",
        "summary": "intent → provider chain; ranks by health + limits.",
        "keywords": "router routing intent free_llm failover health rank sticky",
    },
    {
        "id": "failover",
        "title": "Execute-time failover",
        "path": "src/tollgate/failover.py",
        "summary": "Walk candidates when primary fails mid-request.",
        "keywords": "failover fallback candidates primary secondary",
    },
    {
        "id": "chaos",
        "title": "Chaos / DR inject + failover test",
        "path": "src/tollgate/chaos.py",
        "summary": "tollgate chaos test <provider> — prove DR before production.",
        "keywords": "chaos dr disaster recovery inject outage prove resilience",
    },
    {
        "id": "resilience-score",
        "title": "AI Resilience Score (0–100)",
        "path": "src/tollgate/resilience.py",
        "summary": "Continuous readiness score + warnings.",
        "keywords": "resilience score readiness prove grade",
    },
    {
        "id": "control-plane",
        "title": "Control plane snapshot",
        "path": "src/tollgate/control_plane.py",
        "summary": "GET /v1/control · dashboard HTML — burn, health, headline.",
        "keywords": "control plane dashboard burn provider health headline",
    },
    {
        "id": "openai-compat",
        "title": "OpenAI drop-in /v1/chat/completions",
        "path": "src/tollgate/openai_compat.py",
        "summary": "base_url=http://127.0.0.1:8787/v1 — stream, models, tools.",
        "keywords": "openai chat completions base_url drop-in n8n stream sse",
    },
    {
        "id": "anthropic-compat",
        "title": "Anthropic Messages drop-in /v1/messages",
        "path": "src/tollgate/anthropic_compat.py",
        "summary": "x-api-key consumers; claude-* aliases show routed_from.",
        "keywords": "anthropic messages claude x-api-key routed_from alias",
    },
    {
        "id": "streaming",
        "title": "Token streaming (SSE)",
        "path": "src/tollgate/chat_stream.py",
        "summary": "Upstream stream:true → client SSE → meter after finish.",
        "keywords": "stream streaming sse tokens reasoning_content",
    },
    {
        "id": "distill",
        "title": "Provider distill JSON (SSoT)",
        "path": "src/tollgate/distill/",
        "summary": "Auth, URLs, ops, errors as data — not hardcoded in handlers.",
        "keywords": "distill provider json ssot research ops maps_to",
    },
    {
        "id": "ledger",
        "title": "Usage ledger (fail-closed)",
        "path": "src/tollgate/usage_ledger.py",
        "summary": "keys_usage.json daily counters; corrupt → deny not reset.",
        "keywords": "ledger usage keys_usage tokens calls chars fail-closed",
    },
    {
        "id": "audit",
        "title": "Append-only audit trail + query",
        "path": "src/tollgate/audit_log.py",
        "summary": "audit.jsonl; GET /v1/audit · tollgate audit — who was denied and why.",
        "keywords": "audit audit.jsonl append-only compliance deny admit_deny query who why",
    },
    {
        "id": "daily-report",
        "title": "Daily operator report",
        "path": "src/tollgate/report.py",
        "summary": "tollgate report · GET /v1/report — Protect/Route/Prove brief for CTOs.",
        "keywords": "report daily operator status brief markdown analytics prove",
    },
    {
        "id": "snapshot",
        "title": "Desk snapshot export/import",
        "path": "src/tollgate/snapshot.py",
        "summary": "tollgate snapshot export/import — portable migrate without Key.txt by default.",
        "keywords": "snapshot export import portable usb migrate backup desk",
    },
    {
        "id": "alerts",
        "title": "Structured webhook alerts",
        "path": "src/tollgate/alerts.py",
        "summary": "schema_version 1 events — soft_budget, agent_protection, chaos_dr_*.",
        "keywords": "alert webhook n8n telegram soft_budget agent_protection chaos",
    },
    {
        "id": "consumer-scopes",
        "title": "Consumer scopes (allow/block providers)",
        "path": "src/tollgate/limits.py",
        "summary": "allowed_providers/intents/ops + blocked_* per lane (L3 identity).",
        "keywords": "scope allowlist blocklist allowed_providers intent op L3",
    },
    {
        "id": "freeze",
        "title": "Global admission freeze (kill switch)",
        "path": "src/tollgate/freeze.py",
        "summary": "tollgate freeze — deny all billable traffic; TOLLGATE_FROZEN env.",
        "keywords": "freeze kill switch panic emergency admission frozen",
    },
    {
        "id": "consumers-auth",
        "title": "Consumer auth (id:secret)",
        "path": "src/tollgate/consumers.py",
        "summary": "X-Consumer-Key / Bearer; open mode when no consumers.json.",
        "keywords": "consumer auth secret hash consumers.json open mode admin",
    },
    {
        "id": "cost-guard",
        "title": "Cost guard + high-risk providers",
        "path": "src/tollgate/cost.py",
        "summary": "USD estimates; Google/high_risk off until unlocked.",
        "keywords": "cost usd high_risk google guard soft_warn webhook",
    },
    {
        "id": "config",
        "title": "keys_app.json config + validate",
        "path": "src/tollgate/app_config.py",
        "summary": "GET/POST/PATCH /v1/config; Pydantic validate on write.",
        "keywords": "config keys_app patch validate cost_guard routing",
    },
    {
        "id": "mcp",
        "title": "MCP stdio server + tools",
        "path": "src/tollgate/mcp.py",
        "summary": "python -m tollgate — keys_* tools for Cursor/Claude Desktop.",
        "keywords": "mcp stdio tools keys_ cursor claude desktop",
    },
    {
        "id": "portable",
        "title": "Portable / USB paths",
        "path": "src/tollgate/paths.py",
        "summary": "TOLLGATE_HOME — no machine-local hardcoding.",
        "keywords": "portable usb TOLLGATE_HOME paths desk stick",
    },
    {
        "id": "doctor",
        "title": "Doctor self-diagnose",
        "path": "src/tollgate/doctor.py",
        "summary": "tollgate doctor — install/config issues + actions.",
        "keywords": "doctor diagnose setup install check",
    },
    {
        "id": "n8n",
        "title": "n8n as consumer",
        "path": "docs/N8N.md",
        "summary": "OpenAI base_url, community node, workflow JSONs, smoke.",
        "keywords": "n8n workflow node openai base_url budget-gate",
    },
    {
        "id": "ops-boundary",
        "title": "Ops boundary (cache ≠ agent memory)",
        "path": "src/tollgate/ops_boundary.py",
        "summary": "Ledger/cache hold ops state only — never conversation memory.",
        "keywords": "ops boundary cache memory agent redaction policy",
    },
    {
        "id": "redact",
        "title": "Secret redaction",
        "path": "src/tollgate/redact.py",
        "summary": "Strip keys from errors before circuits/audit/logs.",
        "keywords": "redact secrets mask error log",
    },
    {
        "id": "metrics",
        "title": "Prometheus metrics (+ auth)",
        "path": "src/tollgate/metrics.py",
        "summary": "GET /metrics; auth mode / TOLLGATE_METRICS_TOKEN / PUBLIC opt-out.",
        "keywords": "prometheus metrics scrape /metrics token public auth",
    },
    {
        "id": "circuit-jitter",
        "title": "Configurable circuit jitter",
        "path": "src/tollgate/gateway/circuit.py",
        "summary": "keys_app circuits.jitter_min/max + hard_cooldown_s sticky AUTH_DEAD.",
        "keywords": "jitter circuits cooldown thundering herd hard_cooldown",
    },
    {
        "id": "safe-defaults",
        "title": "Safe default envelopes (Protect on)",
        "path": "src/tollgate/app_config.py",
        "summary": "consumer_envelopes._default ships with $ / rpm / tool_calls caps.",
        "keywords": "safe default envelope protect max_usd_day default",
    },
    {
        "id": "getting-started",
        "title": "5-minute getting started",
        "path": "docs/GETTING_STARTED.md",
        "summary": "Fastest path to a working desk.",
        "keywords": "getting started quickstart setup 5min onboarding",
    },
    {
        "id": "architecture",
        "title": "7-layer architecture",
        "path": "docs/ARCHITECTURE.md",
        "summary": "Vault → distill → identity → admit → router → transport → meter.",
        "keywords": "architecture layers design masterpiece",
    },
    {
        "id": "map",
        "title": "Repo map (this index)",
        "path": "docs/MAP.md",
        "summary": "Human map of modules, HTTP, CLI, tests, configs.",
        "keywords": "map index modules structure searchable find",
    },
]


HTTP_ROUTES: list[dict[str, str]] = [
    {"method": "GET", "path": "/v1/health", "summary": "Portable + auth mode"},
    {"method": "GET", "path": "/v1/auth", "summary": "Auth status"},
    {"method": "GET", "path": "/v1/control", "summary": "Control plane JSON"},
    {"method": "GET", "path": "/v1/status", "summary": "Compact desk status"},
    {"method": "GET", "path": "/v1/resilience", "summary": "Resilience score"},
    {"method": "GET", "path": "/v1/chaos", "summary": "Chaos inject status"},
    {"method": "GET", "path": "/v1/audit", "summary": "Query deny/usage audit trail"},
    {"method": "GET", "path": "/v1/report", "summary": "Daily operator report (json|md)"},
    {"method": "GET", "path": "/v1/alerts", "summary": "Webhook event catalog"},
    {"method": "POST", "path": "/v1/alerts/test", "summary": "Force webhook probe (admin)"},
    {"method": "GET", "path": "/v1/freeze", "summary": "Kill-switch status"},
    {"method": "POST", "path": "/v1/freeze", "summary": "Set admission freeze (admin)"},
    {"method": "GET", "path": "/v1/circuits", "summary": "List circuit breakers"},
    {"method": "POST", "path": "/v1/circuits/reset", "summary": "Reset circuits (admin)"},
    {"method": "GET", "path": "/dashboard", "summary": "HTML control plane"},
    {"method": "GET", "path": "/v1/providers", "summary": "Provider inventory"},
    {"method": "GET", "path": "/v1/budget", "summary": "Budget snapshot"},
    {"method": "POST", "path": "/v1/route", "summary": "Intent → provider"},
    {"method": "POST", "path": "/v1/invoke", "summary": "Admit + call + meter"},
    {"method": "GET", "path": "/v1/usage", "summary": "Usage counters"},
    {"method": "GET", "path": "/v1/config", "summary": "Read policy"},
    {"method": "POST", "path": "/v1/config", "summary": "Patch policy (admin)"},
    {"method": "GET", "path": "/v1/models", "summary": "OpenAI models list"},
    {
        "method": "POST",
        "path": "/v1/chat/completions",
        "summary": "OpenAI chat drop-in (+ stream)",
    },
    {
        "method": "POST",
        "path": "/v1/messages",
        "summary": "Anthropic Messages drop-in",
    },
    {"method": "GET", "path": "/metrics", "summary": "Prometheus text"},
    {"method": "GET", "path": "/docs", "summary": "OpenAPI (FastAPI)"},
    {"method": "GET", "path": "/", "summary": "Root redirect / info"},
]


CLI_COMMANDS: list[dict[str, str]] = [
    {"cmd": "serve", "summary": "Run HTTP server (uvicorn :8787)"},
    {"cmd": "mcp", "summary": "Run MCP stdio server"},
    {"cmd": "health", "summary": "Local health JSON"},
    {"cmd": "control", "summary": "Control plane snapshot"},
    {"cmd": "resilience", "summary": "AI Resilience Score"},
    {"cmd": "chaos", "summary": "Chaos inject / DR test"},
    {"cmd": "paths", "summary": "Portable path snapshot"},
    {"cmd": "consumer-add", "summary": "Add HTTP consumer id:secret"},
    {"cmd": "consumer-budget", "summary": "Day envelopes + agent protection"},
    {"cmd": "provider-add", "summary": "Scaffold distill JSON"},
    {"cmd": "high-risk", "summary": "List/add/remove high-risk providers"},
    {"cmd": "doctor", "summary": "Self-diagnose install/config"},
    {"cmd": "suggest", "summary": "Ledger-based config proposals"},
    {"cmd": "search", "summary": "Search repo modules / docs / routes"},
    {"cmd": "audit", "summary": "Query audit trail — who was denied and why"},
    {"cmd": "report", "summary": "Daily operator report Protect·Route·Prove"},
    {"cmd": "snapshot", "summary": "Export/import desk ops state (USB migrate)"},
    {"cmd": "alert", "summary": "Webhook test / event catalog"},
    {"cmd": "freeze", "summary": "Global admission kill switch"},
    {"cmd": "status", "summary": "Compact desk status one-glance"},
    {"cmd": "circuits", "summary": "List or reset circuit breakers"},
]


# ── entry model ──────────────────────────────────────────────────────


@dataclass
class Entry:
    kind: str  # concept | module | doc | http | cli | config
    title: str
    path: str
    summary: str = ""
    keywords: str = ""
    body: str = ""
    score: float = 0.0
    snippet: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "kind": self.kind,
            "title": self.title,
            "path": self.path,
            "summary": self.summary,
            "score": round(self.score, 2),
        }
        if self.snippet:
            d["snippet"] = self.snippet
        if self.extra:
            d.update(self.extra)
        return d


# ── collectors ───────────────────────────────────────────────────────


def _module_docstring(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    if not text.lstrip().startswith('"""') and not text.lstrip().startswith("'''"):
        # may have from __future__ first
        m = re.search(r'^(?:from __future__.*\n+)?("""|\'\'\')', text, re.M)
        if not m:
            # try first triple-quote block near top
            m2 = re.search(r'("""|\'\'\')(.*?)\1', text[:2000], re.S)
            if not m2:
                return ""
            return " ".join(m2.group(2).split())[:400]
        quote = m.group(1)
        start = m.end()
        end = text.find(quote, start)
        if end < 0:
            return ""
        return " ".join(text[start:end].split())[:400]
    quote = '"""' if text.lstrip().startswith('"""') else "'''"
    raw = text.lstrip()
    start = len(quote)
    end = raw.find(quote, start)
    if end < 0:
        return ""
    return " ".join(raw[start:end].split())[:400]


def collect_modules() -> list[Entry]:
    pkg = package_dir()
    out: list[Entry] = []
    for path in sorted(pkg.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        if path.name.startswith("."):
            continue
        rel = f"src/tollgate/{path.relative_to(pkg).as_posix()}"
        doc = _module_docstring(path)
        title = path.stem if path.name != "__init__.py" else path.parent.name
        if path.name == "__init__.py" and path.parent == pkg:
            title = "tollgate (package)"
        out.append(
            Entry(
                kind="module",
                title=title,
                path=rel,
                summary=doc.split(".")[0][:160] + ("." if doc else ""),
                keywords=f"{title} {path.stem} {doc[:200]}",
                body=doc,
            )
        )
    return out


def collect_docs() -> list[Entry]:
    ddir = docs_dir()
    if not ddir:
        return []
    out: list[Entry] = []
    for path in sorted(ddir.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = f"docs/{path.relative_to(ddir).as_posix()}"
        lines = text.splitlines()
        title = path.stem
        for ln in lines[:30]:
            if ln.startswith("# "):
                title = ln[2:].strip()
                break
        # headings as keywords
        heads = [
            ln.lstrip("#").strip()
            for ln in lines
            if ln.startswith("#") and len(ln) < 120
        ]
        body = text[:8000]
        summary = ""
        for ln in lines:
            s = ln.strip()
            if s and not s.startswith("#") and not s.startswith("|") and not s.startswith("```"):
                summary = s[:200]
                break
        out.append(
            Entry(
                kind="doc",
                title=title,
                path=rel,
                summary=summary,
                keywords=" ".join(heads) + " " + path.stem,
                body=body,
            )
        )
    return out


def collect_concepts() -> list[Entry]:
    return [
        Entry(
            kind="concept",
            title=c["title"],
            path=c["path"],
            summary=c.get("summary", ""),
            keywords=c.get("keywords", "") + " " + c["id"],
            body=c.get("summary", ""),
            extra={"id": c["id"]},
        )
        for c in CONCEPTS
    ]


def collect_http() -> list[Entry]:
    return [
        Entry(
            kind="http",
            title=f"{r['method']} {r['path']}",
            path="src/tollgate/server_v1.py",
            summary=r["summary"],
            keywords=f"{r['method']} {r['path']} {r['summary']} api endpoint route",
            body=r["summary"],
            extra={"method": r["method"], "route": r["path"]},
        )
        for r in HTTP_ROUTES
    ]


def collect_cli() -> list[Entry]:
    return [
        Entry(
            kind="cli",
            title=f"tollgate {c['cmd']}",
            path="src/tollgate/cli.py",
            summary=c["summary"],
            keywords=f"cli {c['cmd']} {c['summary']}",
            body=c["summary"],
            extra={"command": c["cmd"]},
        )
        for c in CLI_COMMANDS
    ]


def collect_configs() -> list[Entry]:
    root = repo_root()
    if not root:
        return []
    out: list[Entry] = []
    for sub, kind_note in (("configs", "config"), ("scripts", "script")):
        d = root / sub
        if not d.is_dir():
            continue
        for path in sorted(d.iterdir()):
            if path.name.startswith("."):
                continue
            if not path.is_file():
                continue
            rel = f"{sub}/{path.name}"
            out.append(
                Entry(
                    kind=kind_note,
                    title=path.name,
                    path=rel,
                    summary=f"{kind_note} in {sub}/",
                    keywords=f"{path.stem} {path.name} {sub}",
                    body=path.stem,
                )
            )
    return out


def all_entries() -> list[Entry]:
    return (
        collect_concepts()
        + collect_modules()
        + collect_docs()
        + collect_http()
        + collect_cli()
        + collect_configs()
    )


# ── scoring ──────────────────────────────────────────────────────────


_TOKEN = re.compile(r"[a-z0-9_./:+-]+", re.I)


def _tokens(q: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(q) if len(t) > 1]


def _score(entry: Entry, tokens: list[str], raw_q: str) -> tuple[float, str]:
    if not tokens:
        return 0.0, ""
    title = entry.title.lower()
    path = entry.path.lower()
    summary = entry.summary.lower()
    keywords = entry.keywords.lower()
    body = entry.body.lower()
    raw = raw_q.lower().strip()

    score = 0.0
    snippet = ""

    # exact phrase boosts
    if raw and len(raw) > 2:
        if raw in title:
            score += 40
        if raw in path:
            score += 25
        if raw in keywords:
            score += 20
        if raw in summary:
            score += 15
        if raw in body:
            score += 8
            # snippet around first match
            idx = body.find(raw)
            if idx >= 0:
                a = max(0, idx - 40)
                b = min(len(entry.body), idx + len(raw) + 60)
                snippet = entry.body[a:b].replace("\n", " ").strip()

    kind_boost = {
        "concept": 12,
        "http": 6,
        "cli": 6,
        "module": 4,
        "doc": 3,
        "config": 2,
        "script": 1,
    }.get(entry.kind, 0)

    hits = 0
    for t in tokens:
        local = 0
        if t in title:
            local += 18
        if t in path or t == Path(entry.path).stem.lower():
            local += 14
        if t in keywords.split():
            local += 10
        elif t in keywords:
            local += 6
        if t in summary:
            local += 5
        if t in body:
            local += 2
            if not snippet:
                idx = body.find(t)
                if idx >= 0:
                    a = max(0, idx - 40)
                    b = min(len(entry.body), idx + len(t) + 60)
                    snippet = entry.body[a:b].replace("\n", " ").strip()
        if local:
            hits += 1
            score += local

    if hits == 0 and score < 8:
        return 0.0, ""

    # all tokens present → bonus
    if hits == len(tokens) and len(tokens) > 1:
        score += 15

    score += kind_boost * (0.15 if hits else 0)
    if not snippet:
        snippet = entry.summary[:120]
    return score, snippet


def search(
    query: str,
    *,
    limit: int = 20,
    kinds: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Search curated index + live modules/docs. Returns ranked hits."""
    q = (query or "").strip()
    tokens = _tokens(q)
    kind_set = {k.lower() for k in kinds} if kinds else None

    hits: list[Entry] = []
    for e in all_entries():
        if kind_set and e.kind not in kind_set:
            continue
        sc, snip = _score(e, tokens, q)
        if sc <= 0:
            continue
        e.score = sc
        e.snippet = snip
        hits.append(e)

    hits.sort(key=lambda x: (-x.score, x.kind, x.path))
    top = hits[: max(1, min(int(limit), 100))]

    return {
        "ok": True,
        "query": q,
        "count": len(top),
        "total_matched": len(hits),
        "kinds": sorted({h.kind for h in top}),
        "hits": [h.as_dict() for h in top],
        "hint": "tollgate search <q> · docs/MAP.md · kinds: concept module doc http cli config script",
    }


def format_search_text(result: dict[str, Any]) -> str:
    lines = [
        f"tollgate search · {result.get('query')!r} · "
        f"{result.get('count')}/{result.get('total_matched')} hits",
        "",
    ]
    if not result.get("hits"):
        lines.append("No hits. Try: circuit, budget, openai, chaos, consumer, distill")
        lines.append("Map: docs/MAP.md")
        return "\n".join(lines)

    for i, h in enumerate(result["hits"], 1):
        kind = h.get("kind", "?")
        title = h.get("title", "")
        path = h.get("path", "")
        score = h.get("score", 0)
        summary = h.get("summary") or h.get("snippet") or ""
        lines.append(f"{i:2}. [{kind}] {title}")
        lines.append(f"    {path}  (score {score})")
        if summary:
            lines.append(f"    {summary[:140]}")
        lines.append("")
    lines.append("See also: docs/MAP.md")
    return "\n".join(lines)


def map_markdown() -> str:
    """Generate docs/MAP.md content from live collectors (for regen)."""
    mods = collect_modules()
    docs = collect_docs()
    lines = [
        "# Tollgate repo map",
        "",
        "> **Search:** `tollgate search <query>` · kinds: concept · module · doc · http · cli",
        "",
        "Living map of modules, HTTP, CLI, docs, configs. "
        "If a path moved, search still finds module docstrings.",
        "",
        "## Product entry",
        "",
        "| Want | Go to |",
        "|------|--------|",
        "| 5-minute setup | [GETTING_STARTED.md](GETTING_STARTED.md) |",
        "| Product wedge | [PRODUCT.md](PRODUCT.md) |",
        "| Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |",
        "| Cost / envelopes | [COST_LIMITS.md](COST_LIMITS.md) |",
        "| OpenAI drop-in | [OPENAI.md](OPENAI.md) |",
        "| Anthropic drop-in | [ANTHROPIC.md](ANTHROPIC.md) |",
        "| n8n | [N8N.md](N8N.md) |",
        "| MCP | [MCP.md](MCP.md) |",
        "| Operations | [OPERATIONS.md](OPERATIONS.md) |",
        "",
        "## HTTP (`tollgate serve` → :8787)",
        "",
        "| Method | Path | Summary |",
        "|--------|------|---------|",
    ]
    for r in HTTP_ROUTES:
        lines.append(f"| `{r['method']}` | `{r['path']}` | {r['summary']} |")
    lines += [
        "",
        "## CLI",
        "",
        "| Command | Summary |",
        "|---------|---------|",
    ]
    for c in CLI_COMMANDS:
        lines.append(f"| `tollgate {c['cmd']}` | {c['summary']} |")
    lines += [
        "",
        "## Concepts → code",
        "",
        "| Concept | Path |",
        "|---------|------|",
    ]
    for c in CONCEPTS:
        lines.append(f"| {c['title']} | `{c['path']}` |")
    lines += [
        "",
        "## Modules (`src/tollgate/`)",
        "",
        "| Module | Summary |",
        "|--------|---------|",
    ]
    for m in mods:
        if m.path.endswith("__init__.py") and "/gateway/" not in m.path and "/distill/" not in m.path:
            if m.path != "src/tollgate/__init__.py":
                continue
        summary = (m.summary or "").replace("|", "/")[:100]
        short = m.path.replace("src/tollgate/", "")
        lines.append(f"| `{short}` | {summary} |")
    lines += [
        "",
        "## Docs",
        "",
        "| Doc | Title |",
        "|-----|-------|",
    ]
    for d in docs:
        lines.append(f"| [`{d.path}`]({d.path.replace('docs/', '')}) | {d.title} |")
    lines += [
        "",
        "## Configs & scripts",
        "",
        "| Path | Role |",
        "|------|------|",
        "| `configs/mcp-tollgate.example.json` | MCP client config |",
        "| `configs/n8n-*.workflow.json` | n8n import workflows |",
        "| `scripts/run.sh` | Start HTTP |",
        "| `scripts/desk-ready.sh` | Desk bring-up |",
        "| `scripts/check_docs_drift.sh` | Doc drift gate |",
        "| `scripts/n8n-smoke.sh` | n8n smoke |",
        "",
        "## Tests",
        "",
        "Contract: `tests/test_contract_v1.py`, `tests/test_openai_compat.py`, "
        "`tests/test_anthropic_compat.py`.  ",
        "Safety: `tests/test_agent_protection.py`, `tests/test_security_ledger.py`, "
        "`tests/test_product_guards.py`.  ",
        "DR: `tests/test_chaos_resilience.py`, `tests/test_failover.py`, "
        "`tests/test_health_routing.py`.  ",
        "Search: `tests/test_repo_search.py`.",
        "",
        "---",
        "",
        "*Regenerate ideas: `python -c \"from tollgate.repo_search import map_markdown; print(map_markdown())\"`*",
        "",
    ]
    return "\n".join(lines)
