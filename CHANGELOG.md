# Changelog

All notable releases of [landjunge/tollgate](https://github.com/landjunge/tollgate).

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
