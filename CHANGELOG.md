# Changelog

All notable releases of [landjunge/tollgate](https://github.com/landjunge/tollgate).

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
