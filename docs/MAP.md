# Tollgate repo map

> **Search:** `tollgate search <query>` · kinds: concept · module · doc · http · cli

Living map of modules, HTTP, CLI, docs, configs. If a path moved, search still finds module docstrings.

## Product entry

| Want | Go to |
|------|--------|
| 5-minute setup | [GETTING_STARTED.md](GETTING_STARTED.md) |
| Product wedge | [PRODUCT.md](PRODUCT.md) |
| Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Cost / envelopes | [COST_LIMITS.md](COST_LIMITS.md) |
| OpenAI drop-in | [OPENAI.md](OPENAI.md) |
| Anthropic drop-in | [ANTHROPIC.md](ANTHROPIC.md) |
| n8n | [N8N.md](N8N.md) |
| MCP | [MCP.md](MCP.md) |
| Operations | [OPERATIONS.md](OPERATIONS.md) |

## HTTP (`tollgate serve` → :8787)

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/v1/health` | Portable + auth mode |
| `GET` | `/v1/auth` | Auth status |
| `GET` | `/v1/control` | Control plane JSON |
| `GET` | `/v1/status` | Compact desk status |
| `GET` | `/v1/resilience` | Resilience score |
| `GET` | `/v1/chaos` | Chaos inject status |
| `GET` | `/v1/audit` | Query deny/usage audit trail |
| `GET` | `/v1/report` | Daily operator report (json|md) |
| `GET` | `/v1/alerts` | Webhook event catalog |
| `POST` | `/v1/alerts/test` | Force webhook probe (admin) |
| `GET` | `/v1/freeze` | Kill-switch status |
| `POST` | `/v1/freeze` | Set admission freeze (admin) |
| `GET` | `/v1/circuits` | List circuit breakers |
| `POST` | `/v1/circuits/reset` | Reset circuits (admin) |
| `GET` | `/dashboard` | HTML control plane |
| `GET` | `/v1/providers` | Provider inventory |
| `GET` | `/v1/budget` | Budget snapshot |
| `POST` | `/v1/route` | Intent → provider |
| `POST` | `/v1/invoke` | Admit + call + meter |
| `GET` | `/v1/usage` | Usage counters |
| `GET` | `/v1/config` | Read policy |
| `POST` | `/v1/config` | Patch policy (admin) |
| `GET` | `/v1/models` | OpenAI models list |
| `POST` | `/v1/chat/completions` | OpenAI chat drop-in (+ stream) |
| `POST` | `/v1/messages` | Anthropic Messages drop-in |
| `GET` | `/metrics` | Prometheus text |
| `GET` | `/docs` | OpenAPI (FastAPI) |
| `GET` | `/` | Root redirect / info |

## CLI

| Command | Summary |
|---------|---------|
| `tollgate serve` | Run HTTP server (uvicorn :8787) |
| `tollgate mcp` | Run MCP stdio server |
| `tollgate health` | Local health JSON |
| `tollgate control` | Control plane snapshot |
| `tollgate resilience` | AI Resilience Score |
| `tollgate chaos` | Chaos inject / DR test |
| `tollgate paths` | Portable path snapshot |
| `tollgate consumer-add` | Add HTTP consumer id:secret |
| `tollgate consumer-budget` | Day envelopes + agent protection |
| `tollgate provider-add` | Scaffold distill JSON |
| `tollgate high-risk` | List/add/remove high-risk providers |
| `tollgate doctor` | Self-diagnose install/config |
| `tollgate suggest` | Ledger-based config proposals |
| `tollgate search` | Search repo modules / docs / routes |
| `tollgate audit` | Query audit trail — who was denied and why |
| `tollgate report` | Daily operator report Protect·Route·Prove |
| `tollgate snapshot` | Export/import desk ops state (USB migrate) |
| `tollgate alert` | Webhook test / event catalog |
| `tollgate freeze` | Global admission kill switch |
| `tollgate status` | Compact desk status one-glance |
| `tollgate circuits` | List or reset circuit breakers |

## Concepts → code

| Concept | Path |
|---------|------|
| Protect · Route · Prove (product pillars) | `docs/PRODUCT.md` |
| Killer demo — agent loop + DR proof | `docs/DEMO.md` |
| Agent protection (loop / $ / RPM hard stops) | `src/tollgate/agent_guard.py` |
| Consumer day envelopes | `src/tollgate/limits.py` |
| L4 Admission (fail-closed) | `src/tollgate/gateway/admit.py` |
| Circuit breaker + cooldown jitter | `src/tollgate/gateway/circuit.py` |
| Health-aware router | `src/tollgate/router.py` |
| Execute-time failover | `src/tollgate/failover.py` |
| Chaos / DR inject + failover test | `src/tollgate/chaos.py` |
| AI Resilience Score (0–100) | `src/tollgate/resilience.py` |
| Control plane snapshot | `src/tollgate/control_plane.py` |
| OpenAI drop-in /v1/chat/completions | `src/tollgate/openai_compat.py` |
| Anthropic Messages drop-in /v1/messages | `src/tollgate/anthropic_compat.py` |
| Token streaming (SSE) | `src/tollgate/chat_stream.py` |
| Provider distill JSON (SSoT) | `src/tollgate/distill/` |
| Usage ledger (fail-closed) | `src/tollgate/usage_ledger.py` |
| Append-only audit trail + query | `src/tollgate/audit_log.py` |
| Daily operator report | `src/tollgate/report.py` |
| Desk snapshot export/import | `src/tollgate/snapshot.py` |
| Structured webhook alerts | `src/tollgate/alerts.py` |
| Consumer scopes (allow/block providers) | `src/tollgate/limits.py` |
| Global admission freeze (kill switch) | `src/tollgate/freeze.py` |
| Consumer auth (id:secret) | `src/tollgate/consumers.py` |
| Cost guard + high-risk providers | `src/tollgate/cost.py` |
| keys_app.json config + validate | `src/tollgate/app_config.py` |
| MCP stdio server + tools | `src/tollgate/mcp.py` |
| Portable / USB paths | `src/tollgate/paths.py` |
| Doctor self-diagnose | `src/tollgate/doctor.py` |
| n8n as consumer | `docs/N8N.md` |
| Ops boundary (cache ≠ agent memory) | `src/tollgate/ops_boundary.py` |
| Secret redaction | `src/tollgate/redact.py` |
| Prometheus metrics (+ auth) | `src/tollgate/metrics.py` |
| Configurable circuit jitter | `src/tollgate/gateway/circuit.py` |
| Safe default envelopes (Protect on) | `src/tollgate/app_config.py` |
| 5-minute getting started | `docs/GETTING_STARTED.md` |
| 7-layer architecture | `docs/ARCHITECTURE.md` |
| Repo map (this index) | `docs/MAP.md` |

## Modules (`src/tollgate/`)

| Module | Summary |
|--------|---------|
| `__init__.py` | Tollgate — multi-consumer API key admission + provider routing. |
| `__main__.py` | python -m tollgate → MCP stdio server. |
| `agent_guard.py` | Agent protection — stop runaway loops before they become invoices. |
| `alerts.py` | Proactive ops alerts (webhook) — soft warn, hard deny, circuit, chaos. |
| `anthropic_compat.py` | Anthropic Messages API facade — drop-in for clients that speak Anthropic format. |
| `app_config.py` | Keys mini-app configuration — user-editable, provider-based. |
| `audit_log.py` | Append-only operational audit trail. |
| `auto_update.py` | Background auto-update of provider status / model caches. |
| `base.py` | Shared helpers for the keys module (masking, env access). |
| `brave.py` | Brave Search — X-Subscription-Token + rate-limit headers. |
| `catalog.py` | Catalog of known key families and which env vars the hub owns. |
| `chaos.py` | Chaos / DR testing — prove failover works before production does. |
| `chat_route.py` | Routed chat: intent → provider/model → gateway admit + call (+ failover). |
| `chat_stream.py` | Real token streaming for OpenAI-compatible providers. |
| `cli.py` | tollgate CLI entry. |
| `client.py` | HTTP client for remote Tollgate instances (n8n, other hosts, agents). |
| `config_validate.py` | Pydantic validation for keys_app. |
| `consumers.py` | Multi-consumer identity for HTTP /v1. |
| `control_plane.py` | AI traffic control plane — product pane over ledger + circuits. |
| `cost.py` | USD cost estimates + generic high-risk provider guards. |
| `dashboard_html.py` | Minimal control-plane HTML — Protect · Route · Prove. |
| `deepseek.py` | DeepSeek / Worker keys — OpenAI-compatible, concurrency-limited. |
| `distill/loader.py` | Load provider distillates — single source of truth for keys functions. |
| `distill/schema.py` | Lightweight distill schema — required fields for provider JSON. |
| `doctor.py` | tollgate doctor — first step after install / USB plug-in. |
| `elevenlabs.py` | ElevenLabs key specials: subscription + credit reserve floor. |
| `failover.py` | Execute-time failover across routed candidates. |
| `filelock.py` | Cross-process exclusive file lock (Unix fcntl; Windows msvcrt). |
| `freeze.py` | Global admission freeze — emergency kill switch for all billable traffic. |
| `gateway/__init__.py` | L4–L7 gateway core: admit → route → call → meter. |
| `gateway/admit.py` | L4 Admission control — fail closed before HTTP. |
| `gateway/circuit.py` | Circuit breaker per (provider, model, key_ref). |
| `gateway/context.py` | Request identity for attribution + request class. |
| `gateway/entry.py` | Single entry for billable ops — admission + service. |
| `gateway/errors.py` | Error taxonomy — different failures need different next actions. |
| `google.py` | Google/Gemini — high-risk; presence only unless explicitly enabled. |
| `httputil.py` | HTTP helpers for key probes (rate-limit headers, safe JSON). |
| `limits.py` | Enforce per-provider and per-consumer call / token / char limits from app_config. |
| `mcp.py` | stdio MCP server for Tollgate (keys admission + router). |
| `mcp_tools.py` | Keys mini-app → MCP tool definitions + handlers. |
| `metrics.py` | Prometheus text exposition from ledger + circuits (no extra deps). |
| `minimax.py` | MiniMax — region-sensitive; pay-as-you-go key vs Token Plan key. |
| `nvidia.py` | NVIDIA NIM cloud — integrate. |
| `openai_compat.py` | OpenAI-compatible facade — drop-in base_url for clients that speak OpenAI format. |
| `opencode_zen.py` | OpenCode Zen gateway — free + paid models via https://opencode. |
| `openrouter.py` | OpenRouter — multi-key chain, credit probe, free-model policy. |
| `ops_boundary.py` | Hard boundary: Tollgate stores operational state only — never agent memory. |
| `paths.py` | Tollgate data paths — portable / USB-friendly, no machine-local hardcoding. |
| `policy.py` | Spend / route policy — preflight before burning credits. |
| `provider_scaffold.py` | Generate a starter distill JSON for a new provider (onboarding). |
| `providers.py` | Thin re-exports — prefer dedicated modules (deepseek, openrouter, …). |
| `redact.py` | Strip secrets from error strings before ledger / circuits / logs. |
| `registry.py` | Minimal ToolSpec for optional registry registration (MCP / host apps). |
| `repo_search.py` | Repo search — make Tollgate source/docs findable without guessing paths. |
| `report.py` | Daily operator report — one pane for Protect · Route · Prove evidence. |
| `research_notes.py` | Provider research — **thin facade over distill/**. |
| `resilience.py` | AI Resilience Score — continuous readiness, not just 'we have circuit breakers'. |
| `response_cache.py` | Operational response cache — NOT agent memory. |
| `router.py` | Provider-based intelligent routing with limits + health-aware ranking. |
| `schema.py` | Unified health schema — every provider status normalizes here. |
| `secrets.py` | Load API secrets from Key. |
| `server_v1.py` | Standalone multi-consumer HTTP surface. |
| `service.py` | KeysService — flagship facade: inventory, dashboard, policy, ops. |
| `snapshot.py` | Desk snapshot export / import — portable migration without guessing paths. |
| `status.py` | Compact operator status — one glance at Protect · Route · Prove. |
| `suggest.py` | Config suggestions from ledger patterns — propose only, never auto-apply. |
| `usage_ledger.py` | Token / call / char ledger — daily buckets, persistent. |

## Docs

| Doc | Title |
|-----|-------|
| [`docs/ANTHROPIC.md`](ANTHROPIC.md) | Anthropic-compatible API |
| [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) | Tollgate — Masterpiece Architecture |
| [`docs/COST_LIMITS.md`](COST_LIMITS.md) | Cost limits (especially Google) |
| [`docs/DEMO.md`](DEMO.md) | Demo: “My AI agent must never go out of control” |
| [`docs/DESK.md`](DESK.md) | Desk runbook (Gnom + n8n + Tollgate) |
| [`docs/GETTING_STARTED.md`](GETTING_STARTED.md) | Getting started in 5 minutes |
| [`docs/KEYS_MODULE.md`](KEYS_MODULE.md) | Tollgate module map |
| [`docs/MAP.md`](MAP.md) | MAP |
| [`docs/MCP.md`](MCP.md) | Tollgate — MCP |
| [`docs/N8N.md`](N8N.md) | n8n + Tollgate |
| [`docs/OPENAI.md`](OPENAI.md) | OpenAI-compatible API |
| [`docs/OPERATIONS.md`](OPERATIONS.md) | Operations: deploy, doctor, auto-maintenance |
| [`docs/PORTABLE.md`](PORTABLE.md) | Portable / USB |
| [`docs/PRODUCT.md`](PRODUCT.md) | Tollgate product direction |
| [`docs/README.md`](README.md) | Tollgate docs |
| [`docs/STABILITY.md`](STABILITY.md) | Scale & future-proofing |
| [`docs/VISION.md`](VISION.md) | Tollgate — Vision (locked) |
| [`docs/providers/INDEX.md`](providers/INDEX.md) | Provider distill index |

## Configs & scripts

| Path | Role |
|------|------|
| `configs/mcp-tollgate.example.json` | MCP client config |
| `configs/n8n-*.workflow.json` | n8n import workflows |
| `scripts/run.sh` | Start HTTP |
| `scripts/desk-ready.sh` | Desk bring-up |
| `scripts/check_docs_drift.sh` | Doc drift gate |
| `scripts/n8n-smoke.sh` | n8n smoke |

## Tests

Contract: `tests/test_contract_v1.py`, `tests/test_openai_compat.py`, `tests/test_anthropic_compat.py`.  
Safety: `tests/test_agent_protection.py`, `tests/test_security_ledger.py`, `tests/test_product_guards.py`.  
DR: `tests/test_chaos_resilience.py`, `tests/test_failover.py`, `tests/test_health_routing.py`.  
Search: `tests/test_repo_search.py`.

---

*Regenerate ideas: `python -c "from tollgate.repo_search import map_markdown; print(map_markdown())"`*
