# Architect assessment — modular enough? (2026-08-13)

**Verdict:** Tollgate is **more modular than a first glance suggests** — but **not cleanly enough decoupled**.  
**Do not** start a big rewrite. **Do** make existing boundaries consistent, **after** real gnom-hub pain is known.

This document freezes the review ranking so Builder work stays scoped.

---

## One-line principle

> **Each module answers one question.**

| Module | Question |
|--------|----------|
| **Protect** | May this happen? |
| **Route** | Where should it happen? |
| **Execute** | Run it. |
| **Account** | What did it cost? |
| **Audit** | What happened? |
| **Prove** | Does Protect + Route actually work? |

---

## Current shape (honest)

```text
                    API / UI
                       │
                       ▼
                gateway/entry.py     ← pipeline stages (facades started)
                       │
            ┌──────────┼──────────┐
            ▼          ▼          ▼
         admit      router     service (KeysService)
            │          │          │
         limits     health     providers × N
         freeze     chaos      ledger, catalog, …
         circuit
```

**Works.** But `service.py` (~900 LOC), `router.py` (~410), `entry.py` (~400) still **know too many friends**.  
**Good cut already:** `admit.py` (~230) — clear “may this request run?” — **do not bloat**.

Facades from Phases 0–7 (`protect/`, `route/`, `prove/`, `identity/`, `accounting/`, `audit/`, `package_deny`) are **import surfaces**, not full decoupling. That is intentional and correct for now.

---

## Ranking

### 🟢 Keep (do not thrash)

- `gateway/admit.py` + `RequestContext`
- Protect · Route · Prove product axes
- Circuit breaker, ledger, audit, chaos/prove, consumers
- Fail-closed on budget/chaos subsystems (product rule)

### 🟠 Refactor later (pain-driven, thin slices)

| Target | Problem | Target shape |
|--------|---------|--------------|
| **`service.py` / KeysService** | God object: imports every provider + limits + router + ledger + registry maps | `providers/registry` + adapter `execute(request)` · KeysService becomes thin façade |
| **`router.py`** | Route **and** execute mixed; ranking + special cases + chaos | `route() → RouteDecision` then separate `execute(decision)` |
| **`gateway/entry.py`** | Still orchestrates too many side-effects (even after stages) | Named modules: pipeline / execution / feedback — **not** a new framework |
| **Free-first truth** | Spread across router prefer_free, `RequestClass.FREE`, `allow_paid_fallback`, config | Single `FreePolicy.resolve(request)` → “may this spend money?” |
| **Provider interface** | deepseek.chat / zen.chat / brave.search differ | Internal `ProviderAdapter` Protocol; adapters own quirks |
| **Decision contracts** | Dicts everywhere | Strengthen: AdmissionDecision · RouteDecision · ExecutionResult (extend existing `Decision` / AdmitDecision) |

### 🔴 Before real production (ops, not aesthetics)

- Security audit (open mode, bind, auth)
- Free-first absolute semantics verified end-to-end
- Concurrency / budget race tests (suite has coverage — keep green)
- OpenAI SDK + streaming integration tests
- Restart/recovery (E2E T5 done — keep in CI script)

### Observability rule (code quality)

Today: many `except Exception: pass` on audit/alert/cache paths.

**Rule:**

```text
Critical path  → fail closed or defined fallback (never silent)
Observability  → fail open + log/metric (never bare pass without log)
```

---

## Target boundaries (enough — no Clean Architecture theater)

```text
              ┌─────────────┐
              │   API/UI    │
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │  Pipeline   │   thin orchestrator only
              └──────┬──────┘
                     │
     ┌───────────────┼───────────────┐
     ▼               ▼               ▼
  PROTECT          ROUTE           PROVE
     │               │               │
     └───────────────┼───────────────┘
                     ▼
              ┌─────────────┐
              │  PROVIDERS  │   adapters + registry
              └──────┬──────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
      ACCOUNTING              AUDIT
```

One process. USB/portable native (no Docker required).

---

## Process (mandatory)

### Phase A — real use (status: largely done 2026-08-13)

gnom-hub-v1: chat, protect, failover, loop, restart, cost lane.  
See `docs/E2E_REPORT_2026-08-13.md`.

### Phase B — collect pain

Only from real desk: streaming quirks, dual-path denials, KeysService growth, free-policy confusion, etc.

### Phase C — boundaries where it hurts

**One slice per change.** Examples (order is suggestion, not a sprint commitment):

1. **RouteDecision only** — `route()` never calls provider execute; `execute_routed` thin glue · **DONE enough**  
2. **KeysService → registry lookup** — `provider_ops.registry` + Protocol stub · **DONE** (full Adapter classes later)  
3. **FreePolicy** — · **DONE** (`protect.free_policy`)  
4. **Observability wrapper** — · **DONE** (`soft_fail`)  
5. **entry stages → private modules** only if entry grows again · **pending**  

**No:** “Grok, modularize everything.”  
**No:** microservices.  
**No:** parallel feature explosion during a slice.

---

## Definition of Done for any future slice

1. Named axis / question in PR body  
2. No public API break without changelog  
3. pytest minimum set + billable-path tests if touched  
4. gnom smoke if Protect/Route/Execute touched  
5. Architect check: no new Protect↔Route wrong-way import  

---

## Relation to Phases 0–7

Phases 0–7 delivered **facades + pipeline stages + dual-path deny parity**.  
That was the right **first** modular step.

This assessment says: **next** work is **deeper cuts on service/router/entry and FreePolicy**, only when pain justifies it — not because modularization is pretty.

---

*Architect source: team review 2026-08-13 · Owner decides go/no-go per slice.*
