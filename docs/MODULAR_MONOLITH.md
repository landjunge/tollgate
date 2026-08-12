# Modular Monolith — target shape (no Big Bang)

**Decision:** Tollgate stays **one process, one deploy**, modular **inside**.  
Not 15 microservices. Not “Grok rewrites 8 000 files.”

**Status:** Phases 0–7 **implemented** (facades + pipeline) · **not** fully decoupled yet.  
**Architect verdict (2026-08-13):** modular enough to keep shipping; **no big rewrite** — deepen boundaries pain-driven.  
→ Full ranking: [`ARCHITECT_ASSESSMENT_2026-08-13.md`](./ARCHITECT_ASSESSMENT_2026-08-13.md)

---

## Product axes (independent)

| Axis | Question | Owns |
|------|----------|------|
| **Protect** | May this request run? | budget, limits, tools, scopes, freeze, policy |
| **Route** | Where does it run? | health, circuit, failover, provider/model, cost preference |
| **Prove** | Do Protect + Route actually work? | chaos, recovery, certificate — **uses** normal modules, no alternate router |

Prove must **not** invent a second routing brain.

---

## Target request pipeline

```text
Request
  → Identity   (consumer / auth)
  → Policy     (scopes, freeze, high-risk)
  → Budget     (day/hour/request)
  → Limits     (tool-loop, RPM, tokens)
  → Routing    (candidates, health, circuit)
  → Provider   (HTTP / SDK)
  → Accounting (ledger, costs)
  → Audit      (append-only ops trail)
```

Each stage returns a **decision** or enriches **context**.  
No stage silently “knows everything.”

---

## Deploy shape

```text
        TOLLGATE (single binary / container)
     ┌──────────────────────────────┐
     │ API  OpenAI · MCP · Admin    │
     │ Engine  pipeline stages      │
     │ Protect · Route · Prove      │
     │ Identity · Ledger · Audit    │
     │ Control Room (dashboard)     │
     └──────────────────────────────┘
                 │
            one deployment
```

Later you *can* peel modules out; only if boundaries already exist.

---

## Current reality (after rework)

`gateway/entry.py` is the **pipeline orchestrator** with named stages:

| Stage | Module |
|-------|--------|
| Prove availability | `prove.availability` |
| Protect admit + rates | `gateway.admit` + `protect.record_rates` |
| Deny packaging | `protect.package_deny` (shared with stream) |
| Execute | `KeysService.call` |
| Route feedback | `gateway.circuit` via `route` facade |
| Accounting reserve | `accounting.try_reserve_day_call` (stream + service) |

Callers: `chat_route`, `chat_stream`, `server_v1`, package root — **public API unchanged**.

---

## Extraction order (safe)

Do **not** start with a full `tollgate/protect/` tree rewrite.

| Phase | Slice | Exit criteria |
|-------|--------|----------------|
| **0** | This doc + freeze new features that cross axes | Team agrees |
| **1** | `entry.py`: named stages as **functions** in place (no package move) — Identity already in ctx; Protect block; Execute; Circuit feedback; Audit | existing tests green |
| **2** | `Decision` / `block()` helper (deny shape one place) | denies look the same |
| **3** | Move chaos gate behind `prove.availability` **facade** (still same files initially) | chaos tests green |
| **4** | Package move only when a folder has **one job** and no circular imports | import graph clean |
| **5** | gnom-hub-v1 E2E after each meaningful phase | T1–T5 style smoke |

**Start file:** `gateway/entry.py` — best indicator that “one module knows too much.”

---

## Rules for Grok / agents

1. **No** “make everything modular” mega-PR.  
2. New feature: name **which axis** (Protect / Route / Prove / Identity / Accounting / Audit).  
3. Prove features call production Path (router + gateway), not a parallel implementation.  
4. After each extraction: `pytest` + short gnom smoke if billable path touched.  
5. Dashboard is **control**, not a second source of truth for policy.

---

## Target tree (eventual — not a to-do list for this week)

```text
tollgate/
  api/          openai, mcp, admin
  core/         request, context, decision, errors
  protect/      budget, limits, freeze, policy
  route/        router, health, circuit, providers
  prove/        chaos, recovery, certificate
  identity/     consumers
  accounting/   ledger, costs
  audit/        audit
  control/      dashboard, snapshots
```

Folders appear when a slice is **ready**, not as empty scaffolding.

---

## Team execution plan

**Concrete phases, tickets, DoD, roles:**  
→ [`docs/TEAM_PLAN_MODULAR_REWORK.md`](./TEAM_PLAN_MODULAR_REWORK.md)

## Done / next

| Done | Next (only if pain) |
|------|---------------------|
| Facades protect/route/prove + entry stages | KeysService → provider registry |
| Dual-path deny packaging | `route()` vs `execute()` split |
| E2E gnom T1–T5 | FreePolicy single source of truth |
| admit.py kept lean | Observability: no bare `except: pass` |

**Product:** daily gnom-hub-v1. **Builder:** one boundary slice when Owner says go — see assessment doc.
