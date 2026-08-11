# Tollgate — Vision (locked)

**Product / repo:** **[landjunge/tollgate](https://github.com/landjunge/tollgate)**  
**Status:** agreed 2026-08-11 · **name locked** · own repo shipped  
**One-liner:** Die Mautstelle für AI-API-Calls — Admission, Budgets, Routing. Gnom ist *ein* Client, nicht der Eigentümer der Wahrheit.

**Why Tollgate:** Every request passes a controlled gate; hard caps prevent bill shock; multi-consumer lanes (Gnom, n8n, agents) share one ledger.

**Tagline:** *Pay the toll — or don't call.*

---

## Destination

```
Gnom-Hub ──┐
n8n ───────┼──►  tollgate (own repo)  ──► Provider APIs
Cursor/MCP ┤         HTTP + MCP + optional
Agents ────┘         OpenAI-compatible /v1
```

| Property | Target |
|----------|--------|
| Repo | `tollgate` |
| Package / CLI | `tollgate` |
| Service id | `tollgate` |
| Consumers | Gnom, n8n, OpenClaw, Cursor, CLI, other agents |
| Control | Budgets, limits, Google hard-off, circuits, audit |
| Truth | `distill/*.json` (docs → data, not code thrash) |
| Shipping | **Own repo** (versioned, CI, changelog) |
| Gnom role | First-class **client**, thin integration |
| Env prefix (future) | `TOLLGATE_*` (in-hub still `GNOM_WS` / keys_app paths) |

---

## Why

- Jeder Agent neu Keys/Limits bauen = Bill shock + Drift  
- n8n braucht dieselben Caps wie der Desk  
- Google/Gemini bleibt zentral gesperrt, nicht pro Tool versteckt  
- Ein Fail-closed Admission-Punkt für alle

---

## Public contract (stable, multi-consumer)

These shapes should survive the repo split:

| Surface | Purpose |
|---------|---------|
| `POST /v1/route` | intent + estimates → provider/model + fallbacks |
| `POST /v1/invoke` | admit + call + meter (`agent_id`, `job_id`, `request_class`) |
| `GET  /v1/budget` | remaining calls/tokens/usd |
| `GET  /v1/health` | liveness + circuit summary |
| `GET  /v1/providers` | inventory grades (masked) |
| MCP stdio | same ops as `keys_*` tools (`tollgate` MCP server) |
| Later | `POST /v1/chat/completions` (OpenAI-compatible for n8n) |

**Consumer auth (required before multi-tenant trust):**  
API key per consumer (`gnom`, `n8n`, `cursor`, …) with **own** daily envelope.

---

## Gateway memory / cache (direction)

Own operational memory — **not** Gnom agent memory (wishes, project HTML).

| Store | Role |
|-------|------|
| Ledger | tokens, $, calls per day / consumer |
| Circuits | open/half-open cooldowns shared by all clients |
| Health EWMA | soft scores for routing |
| Response cache | optional TTL for search / free chat (saves quota) |
| Dead-key memory | AUTH_DEAD without 401 storms |

Policy sketch: prefer cache for `batch`/`free`; `interactive` often fresh.  
Lives with the **own-repo** gateway (SQLite first; Redis only if multi-host).

---

## Roadmap

| Phase | Outcome | Status |
|-------|---------|--------|
| 0 | Control plane in gnom-hub (distill, cost_guard, MCP, admit/circuit) | **done** |
| 1 | Extractable package + standalone HTTP `/v1/*` | **done (v0.1)** — `keys.server_v1` as Tollgate |
| 2 | Seal all Gnom spend through Tollgate | **done** (client + tools + UI) |
| 3 | Consumer API keys + per-consumer budgets | **done** (hash auth + envelopes) |
| 4 | **Own repo `tollgate`** + CI + version tags | **done** |
| 5 | n8n: HTTP workflows → community node | docs: `N8N.md` + OpenAI drop-in |
| 6 | Optional OpenAI-compatible proxy | **done** (`/v1/chat/completions`) |
| 7 | Optional quality/semantic routing | later |

---

## Non-goals (for now)

- Replacing OpenRouter/LiteLLM as a global SaaS  
- Multi-user SaaS multi-tenancy in the cloud  
- Semantic routing before admission is boring and correct  
- Mixing agent long-term memory into Tollgate  

---

## Success

1. n8n workflow can `route` + `invoke` without holding provider secrets.  
2. Gnom agents use the same service.  
3. Google cannot spend unless explicitly unlocked with hard `$` caps.  
4. Runaway loop → hard deny + audit, not invoice.  
5. Repo `tollgate` can leave gnom-hub without rewriting clients (stable `/v1` + MCP).
