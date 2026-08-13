# Changelog

All notable releases of [landjunge/tollgate](https://github.com/landjunge/tollgate).

## Unreleased

### Refactor — modular monolith (Phases 0–7 complete)
- **Pipeline stages** in `gateway/entry.py` (prove → protect admit → rates → cache → execute → circuit)
- **`gateway/decision.py`**: unified deny `Decision` + `from_admit_decision`
- **`protect.package_deny`**: single deny packaging (audit + alert + block card) for **gateway + stream**
- **`prove/`**: availability facade — entry, router, stream hops
- **`protect/`**: evaluate_protect · record_rates · freeze/rates re-exports
- **`route/`**: select_route · circuit feedback facade
- **`identity/` · `accounting/` · `audit/`**: light axis facades (Phase 7)
- Stream: prove gate + rates + day-call reserve; deny shape matches non-stream
- Docs: `TEAM_PLAN_MODULAR_REWORK.md`, `MODULAR_MONOLITH.md`
- Tests: `test_modular_pipeline.py` (deny parity, import rule) · **181** pytest green
- Chaos prove path uses `route.select_route` (no alternate router)
- E2E: `scripts/e2e-gnom-hub.sh all` covers T1–T5 + gnom API + restart · report in docs
- **Portable/USB first (no Docker):** README/GETTING_STARTED native-first; `portable-setup` requires Python ≥3.10; `portable-smoke.sh`; Gnom co-layout on stick documented
- Docs: architect assessment — modular enough, no big rewrite; pain-driven boundary slices (`ARCHITECT_ASSESSMENT_2026-08-13.md`)
- **M10 FreePolicy:** `protect.free_policy.resolve` / `order_chain` / `admit_free_gate` — one free/paid truth for router + admit
- **M11 soft_fail:** observability failures log + count (entry cache/rates/audit) — no silent `except: pass`
- **M8:** `route()` vs `execute_routed()` kept separate (Prove can route-only); `RouteDecision` type
- **M9:** Provider op maps moved to `provider_ops/registry.py`; KeysService looks up ops — no per-provider imports in service
- **Code revive R1 (team):** post-M9 NameErrors; `GET /` product key; doctor live map; audit facade; scope/stream fail-closed; corrupt `consumers.json` / `keys_app.json` / `circuits.json` fail-closed; doctor readiness honest on corrupt auth; `circuits_corrupt` on Route facade; `soft_fail`; `docs/CODE_REVIVE_2026-08-13.md` · `TEAM_PLAN` R1 closed
- **M6b:** `chat_stream` uses `entry` prove/admit/rates stages (same Protect path as `gateway_call`)

## 1.0.13 — 2026-08-11

### Website SEO / Google indexing
- Full meta: keywords, robots, googlebot, canonical, hreflang EN/DE
- Open Graph + Twitter cards · `assets/og.png` (1200×630)
- JSON-LD: SoftwareApplication, WebSite, FAQPage (EN/DE), CollectionPage (docs)
- Enhanced `sitemap.xml` (hreflang + image) · `robots.txt`
- Visible FAQ section on landing for crawlable answers

## 1.0.12 — 2026-08-11

### Cold path / Prove friction
- Default `free_llm` chain includes **deepseek** (so chaos has a keyed fallback)
- Demo soft-adds deepseek to free_llm when missing; chaos report `next_step` + tried skips
- ten-minute stranger checklist; n8n-smoke protect + certificate
- n8n node **0.2.1**: Certificate op + clearer toolCallsEst help
- doctor warns when free_llm is enabled but not keyed

## 1.0.11 — 2026-08-11

### Product friction (not features)
- Version aligned (package was behind site 1.0.10)
- **tool_calls_est**: infer from message history + header `X-Tollgate-Tool-Calls-Est`; docs OPENAI/N8N/FAQ
- **Chaos NOT_RUN**: honest next steps in certificate, Control Room Prove pane, CLI help, attention text
- `estimate_tool_calls_est()` in `openai_compat` for OpenAI drop-in

## 1.0.10 — 2026-08-11

### Site redesign — ops desk, not SaaS template
- Full visual rewrite: amber/CRT night-shift desk, IBM Plex, sharp edges
- Hero + admission console side-by-side (Protect/Route/Prove is the product)
- Failure-mode rows instead of emoji feature cards
- SVG architecture schematic; Control Room as instrument panel
- Keep copy UX (clipboard + fallback + toast)

## 1.0.9 — 2026-08-11

### Product landing (not OSS brochure)
- Rebuild `site/` as product story: hero → **animated Protect/Route/Prove demo** → why → architecture → dashboard mock → stack → quickstart → prove → dev details last
- DE parity (`de.html`); no feature-catalog positioning
- Copy: “Protect your AI agents in production.”

## 1.0.8 — 2026-08-11

### Product website (GitHub Pages)
- Static site in `site/` — EN landing, DE page, docs index
- Control Room aesthetic · Protect · Route · Prove positioning
- Workflow `.github/workflows/pages.yml` → https://landjunge.github.io/tollgate/

## 1.0.7 — 2026-08-11

### Documentation & help (expanded)
- `docs/HILFE.md` — full DE handbook (+ env, config recipes, admit path, recipes, glossary, FAQ)
- `docs/USER_GUIDE.md` — EN parity with DE handbook
- `docs/FAQ.md` — standalone FAQ
- CLI help topics: `env`, `config`, `faq` (+ existing start/protect/…)
- Dashboard footer → FAQ link; indexes updated

## 1.0.6 — 2026-08-11

### Documentation & help
- `docs/HILFE.md` — detailed German handbook
- `docs/USER_GUIDE.md` — detailed English handbook
- CLI: `tollgate help [topic]` (start, protect, route, prove, ui, api, ops, …)
- Docs index + dashboard footer + README links

## 1.0.5 — 2026-08-11

### WebUI polish (UX, not features)
- **Test tool-loop block** in browser (Overview + Agents) → 🛑 modal
- **Edit protection** on agent detail (save via `/v1/config`)
- Cost split on Overview (by agent / provider)
- Auto loop-test after onboarding finish; Unfreeze button when frozen
- Persist API key label in localStorage

## 1.0.4 — 2026-08-11

### WebUI — first-agent onboarding
- 4-step wizard: welcome → name agent → protection → done
- Writes `consumer_envelopes` via `/v1/config` (no CLI required for first lane)
- Auto-shows when no protected agents; **Setup** button to re-run
- Still five main screens — Settings stay out of nav

## 1.0.3 — 2026-08-11

### WebUI — Control Room (simple, not dense)
- Multi-screen dashboard: **Overview · Agents · Providers · Prove · Audit**
- Status badge: PROTECTED / ATTENTION / FROZEN
- Recommendations with fix hints; Prove runs `POST /v1/chaos/test`
- `GET /v1/certificate` for scorecard in UI
- Agent detail shows protection + scopes (edit still CLI)

## 1.0.2 — 2026-08-11

### Product / onboarding (not feature density)
- **10-minute cold path:** `docs/TEN_MINUTE.md` + `./scripts/ten-minute.sh`
- README leads with stranger install → Protect → Prove → scorecard
- `tollgate certificate` — AI Reliability Report PASS/FAIL card (desk evidence)
- Process lock: feedback > features until cold path is trivial

## 1.0.1 — 2026-08-11

### Added
- `./scripts/demo-agent-safety.sh` and `tollgate demo` — live two-Aha flow
- Deny payloads include product card `blocked` / `message` (🛑 REQUEST BLOCKED)
- OpenAI/Anthropic error.tollgate carries the same card

## 1.0.0 — 2026-08-11

**First stable community release** — Protect · Route · Prove.

**Positioning lock:** *“My AI agent must never go out of control.”*  
Tollgate is the **safety layer** between AI agents and the internet — not an API gateway.  
Demo script: `docs/DEMO.md`.

Self-hosted AI reliability & control plane: pre-admission hard stops, multi-consumer
envelopes, health-aware failover, chaos/DR proof, and operator surfaces (CLI, HTTP,
MCP, dashboard). Not another LLM catalog proxy.

### Stable contract (v1)

| Surface | Role |
|---------|------|
| `POST /v1/route` · `POST /v1/invoke` | Intent route + admit/call/meter |
| `POST /v1/chat/completions` · `POST /v1/messages` | OpenAI / Anthropic drop-ins |
| `GET /v1/control` · `/dashboard` | Control plane pane |
| `GET /v1/status` · `GET /v1/report` · `GET /v1/audit` | Ops glance / day brief / trail |
| `GET|POST /v1/freeze` · `GET|POST /v1/circuits/*` | Kill switch · circuit ops |
| `GET /metrics` | Prometheus (auth when consumers / token) |
| MCP stdio · `tollgate` CLI | Same product, agent & shell |

### Protect
- Safe `_default` envelopes · agent protection (rpm / $ / tool loops)
- Consumer scopes (allow/block providers · intents · ops)
- Global freeze kill switch (fail-closed) · fail-closed ledger
- Secret redaction · metrics/config auth · structured webhooks

### Route
- Health-aware ranking · execute-time failover
- Circuit breakers (disk + FileLock + mtime live reload · jitter)

### Prove
- Chaos inject / failover tests · AI Resilience Score
- Doctor reliability policy · chaos history on dashboard

### Ops & portable
- Snapshot export/import · desk status · n8n node v0.2
- `docs/MAP.md` · `llms.txt` · `tollgate search`

### Compatibility
- **Requires Python ≥ 3.11**
- Config shape remains `keys_app.json` version 2 (forward-compatible extras allowed)
- Breaking changes after 1.0.0 will target `/v2` or a minor with deprecation notes

Earlier history: 0.2.x foundation through 0.3.8 review harden (below).

## 0.3.8 — 2026-08-11

### Fixed (deep review)
- Freeze kill switch is **fail-closed** if `tollgate.freeze` itself errors (no silent pass)
- Circuit registry **re-reads** `circuits.json` on mtime change (multi-worker live share)
- Docs: metrics auth lives in `server_v1` route (noted in `metrics.py`)
- Test: ledger corrupt → `check_limits` → `admit` deny end-to-end

## 0.3.7 — 2026-08-11

### Added
- `tollgate status` / `GET /v1/status` — compact freeze · resilience · spend · attention
- MCP `keys_desk_status`
- Success response headers: `X-Tollgate-Provider`, `Consumer`, `Model`, `Routed-From/To`, cache/failover
- Report includes admission freeze line

## 0.3.6 — 2026-08-11

### Added
- Global admission freeze kill switch: `tollgate freeze` / `unfreeze`, `GET|POST /v1/freeze`, MCP `keys_freeze`
- Env override `TOLLGATE_FROZEN=1`
- Circuit reset: `tollgate circuits list|reset`, `POST /v1/circuits/reset`
- Dashboard freeze banner + control plane `freeze` blob
- Webhook events `admission_frozen` / `admission_unfrozen`

## 0.3.5 — 2026-08-11

### Added
- Consumer scopes (L3): `allowed_providers` / `blocked_providers`, ops, intents
- CLI: `tollgate consumer-budget … --allow-provider|intent|op --block-* --clear-scopes`
- Enforced on admit, route, and chat paths (`protection: scope`)

## 0.3.4 — 2026-08-11

### Added
- Structured webhook alerts (`schema_version: 1`) with severity + event catalog
- `tollgate alert test` / `tollgate alert events`
- `GET /v1/alerts`, `POST /v1/alerts/test` (admin)
- MCP `keys_alert_test`
- Chaos lifecycle alerts: started / stopped / DR survived|failed
- Example n8n workflow: `configs/n8n-webhook-alerts.workflow.json`

## 0.3.3 — 2026-08-11

### Added
- Desk snapshot export/import (`tollgate snapshot`) — portable migrate without Key.txt by default
- OpenAI chat extras: `tool_calls_est`, `tokens_est` (loop protection on drop-in)
- n8n community node v0.2: control, report, resilience, audit ops

## 0.3.2 — 2026-08-11

### Added
- Daily operator report: `tollgate report`, `GET /v1/report`, MCP `keys_report`
- OpenAI/Anthropic deny metadata: `error.tollgate` + `Retry-After` / `X-Tollgate-*` headers

## 0.3.1 — 2026-08-11

### Added
- Audit trail query: `tollgate audit`, `GET /v1/audit`, dashboard recent denies, MCP `keys_audit`

## 0.3.0 — 2026-08-11

### Added
- Protect-on-by-default `_default` envelopes
- Configurable circuit jitter + sticky hard cooldown (`keys_app.circuits`)
- Metrics auth when consumers required or `TOLLGATE_METRICS_TOKEN` set

## 0.2.9 — 2026-08-11

### Added
- Local repo search: `tollgate search`, `docs/MAP.md`, `llms.txt`

## 0.2.8 — 2026-08-11

### Fixed
- Config PATCH validates live
- Anthropic `claude-*` aliases surface `routed_from` (no silent rewrite)

## 0.2.4 – 0.2.7

- Chaos / DR tests + AI Resilience Score
- Reliability policy + gradual recovery
- Doctor reliability checks + dashboard DR panel
- Getting started + invoke/MCP tool-call protection

## 0.2.0 – 0.2.3

- Multi-consumer auth, envelopes, agent protection
- Health-aware routing, control plane, product positioning

## 0.1.x

- Foundation: admit, distill, OpenAI/Anthropic drop-ins, MCP, portable paths
