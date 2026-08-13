# Team-Plan: Modularer Monolith Umbau (Tollgate)

**Zielarchitektur:** intern modular, **ein** Deployable (kein Microservice-Zoo).  
**Methode:** inkrementell · eine Phase · grüne Tests · dann gnom-hub-v1.  
**Startpunkt:** `gateway/entry.py` (weiß zu viel).  
**Nicht-Ziel:** Big-Bang-Rewrite, Feature-Explosion, 15 Docker-Services.

**Dokumente:**
- `docs/MODULAR_MONOLITH.md` — Vision & Regeln  
- `docs/ARCHITECTURE.md` — L1–L7 Produktarchitektur  
- **dieses Doc** — konkreter Umsetzungsplan fürs Team  

**Stand:** 2026-08-13 · Status: **PLAN COMPLETE**  
- Phases **0–7 DONE** (181 pytest green)  
- M3b: chaos uses `route.select_route` + production `routed_chat`  
- E2E T1–T5 + gnom API: **13/13 PASS** → `docs/E2E_REPORT_2026-08-13.md`
---

## 1. Team-Rollen (wer macht was)

| Rolle | Verantwortung | Entscheidet |
|-------|----------------|-------------|
| **Owner / Product** (du) | Priorität Protect/Route/Prove, Abnahme gnom-E2E, „kein Feature jetzt“ | Go / No-Go pro Phase |
| **Architect** (Reviewer) | Modulgrenzen, Dependency-Violations, Fail-closed-Semantik | PR-Architektur-Review |
| **Builder** (Grok / Dev) | Implementierung **einer** Phase, Tests, kein Scope-Creep | Code innerhalb Phase-Scope |
| **QA / Real-path** | gnom-hub-v1 Smoke nach billable-path-Phasen | T1–T5-ähnlich PASS/FAIL |

**Arbeitsregel:** Builder liefert PR nur für **eine** Phase. Architect lehnt ab, wenn neue Imports die Achsen mischen (z. B. Prove-Chaos in Protect-Budget).

---

## 2. Zielbild (kurz)

```text
                    ┌─────────────────────┐
                    │     Tollgate API    │
                    │  OpenAI / MCP / Admin│
                    └──────────┬──────────┘
                               │
                     ┌─────────▼─────────┐
                     │  Request Engine   │  ← pipeline, context, decision
                     └─────────┬─────────┘
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
      🛡 PROTECT          🧭 ROUTE            🧪 PROVE
      budget/limits       health/circuit      chaos/recovery
      freeze/policy       failover/router     certificate
           │                   │                   │
           └───────────────────┼───────────────────┘
                               ▼
                    Ledger · Audit · Identity
```

**Request-Pipeline (Soll):**

```text
Identity → Policy → Budget → Limits → Routing → Provider → Accounting → Audit
```

**Deploy:** ein Prozess / ein Container. Module = Ordner + klare Imports, **nicht** Netzwerk-Services.

---

## 3. Ist-Zustand (Fakten aus Code)

### 3.1 `gateway_call` mischt Achsen

| Schritt heute in `entry.py` | Achse |
|-----------------------------|--------|
| `chaos.is_provider_unavailable` | Prove (inject) |
| `admit()` (freeze, limits, circuit pre-check) | Protect (+ Circuit-Anteil) |
| `agent_guard.record_attempt` | Protect (short window) |
| `response_cache` | Ops / Route-Nebenpfad |
| `KeysService.call` | Provider execute |
| `circuits.success/failure` | Route feedback |
| `audit` / `alerts` / `block_view` | Audit / UX |

**Importers von `gateway.entry`:** `chat_route`, `chat_stream`, `server_v1`, package `__init__` → **öffentliche API darf nicht brechen.**

### 3.2 Parallel-Pfade (Risiko)

| Pfad | Problem für Modularisierung |
|------|------------------------------|
| `chat_stream` ruft `admit` **direkt** | umgeht teilweise entry (Rates/reserve historisch fixen) |
| `router` ruft `admit` | Routing mischt Protect |
| `chaos` hat eigene Route-Schleifen | Prove darf **nicht** eigenen Router erfinden |
| `service.call` macht Limits + reserve + ledger | Accounting/Protect doppelt im Stack |

### 3.3 Pflicht-Tests pro Phase (Minimum)

```text
pytest -q \
  tests/test_chaos_fail_closed.py \
  tests/test_chaos_resilience.py \
  tests/test_failover.py \
  tests/test_concurrency.py \
  tests/test_ledger_fail_closed_chain.py \
  tests/test_security_ledger.py \
  tests/test_openai_compat.py \
  tests/test_server_v1.py
```

Nach Phasen die **billable path** berühren zusätzlich:

```text
# gnom-hub-v1 smoke (manuell oder scripts)
T1 Normal chat · T2 Protect visible · T4 Restart (optional) · T5 Chaos
```

---

## 4. Phasenplan (konkret)

### Phase 0 — Freeze & Vertrag (0,5 Tag)

**Owner:** Product + Architect  

| Deliverable | Details |
|-------------|---------|
| Scope freeze | Keine neuen Features außer Phase-Slices + Critical Bugs |
| Public API freeze | `gateway_call`, `admit`, OpenAI `/v1/chat/completions`, CLI `chaos`/`consumer-budget` |
| Module map | Diese Datei + `MODULAR_MONOLITH.md` als Source of Truth |
| Definition of Done (DoD) | siehe §6 |

**Exit:** Team-OK „wir bauen Phase 1, nichts anderes“.

---

### Phase 1 — `entry.py` als Pipeline (ohne Package-Move) · **1–2 Tage**

**Owner:** Builder · **Review:** Architect  

**Was:** `gateway_call` in **benannte private Steps** zerlegen, **gleiche Datei** (oder `gateway/pipeline_steps.py` nur wenn nötig):

```text
1. stage_prove_availability(provider)     # chaos / recovery gate
2. stage_protect_admit(...)               # admit + deny package
3. stage_protect_rates(...)               # agent_guard
4. stage_cache_lookup(...)                # optional early return
5. stage_execute(...)                     # KeysService.call
6. stage_route_feedback(...)              # circuit success/fail
7. stage_cache_store(...)                 # optional
```

Deny-Pfad: **eine** Hilfsfunktion `build_deny(...)` (audit + alert + block_view) — keine Copy-Paste-Blöcke.

**Nicht in Phase 1:**
- Ordner `protect/` `route/` `prove/` anlegen und half-move  
- `chat_stream` umbauen  
- Dashboard  
- neue Features  

**Akzeptanz:**
- [ ] Alle Tests §3.3 grün  
- [ ] Öffentliche Signatur `gateway_call` unverändert  
- [ ] Keine Verhaltensänderung (Fail-closed Chaos bleibt)  
- [ ] Kurzer Diff-Review: Stages lesbar in &lt;2 min  

**PR-Titel-Vorschlag:** `refactor(gateway): pipeline stages inside entry (no API break)`

---

### Phase 2 — `Decision` / Deny-Contract · **1 Tag**

**Owner:** Builder  

**Was:**
- Kleines `core/decision.py` (oder `gateway/decision.py` vorerst):  
  `allowed`, `error_class`, `reason`, `extra`, `as_http_dict()`, `to_openai_error()`  
- Alle Denies aus Stage 1–3 nutzen denselben Typ  
- `AdmitDecision` bleibt; Mapping `AdmitDecision → Decision` an einer Stelle  

**Akzeptanz:**
- [ ] Deny-Responses aus OpenAI-Compat / invoke / gateway haben gleiche Kernfelder  
- [ ] Tests: block_view, product_guards, openai_compat grün  

**PR:** `refactor(core): unified deny Decision for protect path`

---

### Phase 3 — Prove-Facade (Chaos ohne Alternativ-Router) · **1–2 Tage**

**Owner:** Builder · **Review:** Architect (streng)  

**Was:**
- Neue schlanke API z. B. `prove.availability.check(provider) → Allow|Divert`  
- `entry` und `router` rufen **nur** die Facade (kein `from tollgate.chaos import …` in entry)  
- Chaos-**Test** (`chaos.test` / CLI / `/v1/chaos/test`) muss `route()` + `gateway_call` / routed path verwenden, **keine** private Kopie der Router-Logik  

**Akzeptanz:**
- [ ] `test_chaos_*` grün  
- [ ] `test_chaos_fail_closed` grün  
- [ ] Chaos-Report: survived/failover_pct unverändert im Happy-Path  
- [ ] Architect bestätigt: kein zweiter Router  

**PR:** `refactor(prove): availability facade; chaos uses production route path`

---

### Phase 4 — Protect-Paket (Verschieben, kein Rewrite) · **2 Tage**

**Owner:** Builder  

**Was (nur Moves + re-exports):**

```text
tollgate/protect/
  __init__.py          # public: evaluate_protect / re-exports
  freeze.py            # thin re-export or move from freeze.py
  limits.py            # later — initially import from tollgate.limits
  rates.py             # agent_guard surface
```

Zuerst **Fassade**, die bestehende Module aufruft. Physischer Move von `limits.py` erst wenn Import-Graph sauber.

**Akzeptanz:**
- [ ] `from tollgate.protect import …` für neue Call-Sites  
- [ ] Alte Imports bleiben als Deprecation-Shim **eine** Version  
- [ ] Full unit suite grün  

**PR:** `refactor(protect): facade package over admit/limits/rates`

---

### Phase 5 — Route-Paket + Circuit/Failover · **2–3 Tage**

**Was:**
- `tollgate/route/` Fassade: `select_candidates`, `record_success/failure`  
- `router.py` / `failover.py` / `gateway/circuit.py` bleiben Logik-Träger bis Graph sauber  
- **Regel:** Router darf `protect.evaluate` aufrufen, aber Protect darf **nicht** Router importieren  

**Akzeptanz:**
- [ ] Import-Linter oder manuelle Regel: no `protect → route` cycle  
- [ ] failover + health_routing + free_llm_no_spillover grün  

---

### Phase 6 — Dual-Path bereinigen (`chat_stream` / `service`) · **DONE**

**Was geliefert:**
- Stream + gateway: `protect.package_deny` / `package_deny_from_admit` (blocked card, audit, same fields)  
- Stream: prove availability gate + rates + `accounting.try_reserve_day_call`  
- `service.call` limit deny carries `error_class` + `protection`  

**Akzeptanz:**
- [x] Stream + non-stream: same deny packaging (`blocked` card)  
- [x] Live T1 chat OK · T2 max_tokens_request blocked with REQUEST BLOCKED  
- [x] Concurrent budget tests in suite  

---

### Phase 7 — Package-Layout „Endzustand light“ · **DONE (facades)**

Axis packages exist as **import facades** (logic stays in proven modules):

```text
protect/     admit · limits · rates · freeze · package_deny
route/       router · failover · circuits
prove/       availability (chaos gate)
identity/    consumer normalize / envelopes
accounting/  try_reserve_day_call · record_usage
audit/       append_audit · query_audit
```

**Not done (by design):** physical moves of `limits.py` / `usage_ledger.py` / `server_v1` into `api/` — no behavior risk, no benefit until import graph needs it.  
Optional later: one package per PR if a file becomes multi-thousand LOC.

---

## 5. Was wir explizit **nicht** tun

| Anti-Pattern | Warum |
|--------------|--------|
| budget-service + router-service + … | Overhead, kein Nutzen für Desk/Single-Node |
| „Grok, modularisiere alles“ | Regression-Lawine |
| Prove mit eigenem Router | Falsche Zertifikate, doppelte Bugs |
| Feature parallel (neue Provider, Org layer) | zerstört Diff-Lesbarkeit |
| Dashboard-Redesign während Phase 1–3 | UI ≠ Modulgrenzen |

---

## 6. Definition of Done (jede Phase)

1. Scope der Phase in PR-Beschreibung (Bullet: in / out)  
2. `pytest` Minimum-Set grün (+ erweiterte Suite wenn billable path)  
3. Kein Public-API-Break ohne Changelog-Eintrag  
4. Architect-Review: Achsen-Trennung  
5. Bei Phase ≥ 3: gnom smoke (mindestens T1 Protect-off / T2 optional)  
6. `CHANGELOG.md` unter Unreleased: `refactor:` Zeile  

---

## 7. Zeitplan (Richtwert)

| Woche | Fokus |
|-------|--------|
| **W1** | Phase 0 + Phase 1 (entry pipeline) |
| **W1–W2** | Phase 2 (Decision) |
| **W2** | Phase 3 (Prove facade) |
| **W3** | Phase 4 (Protect facade) |
| **W3–W4** | Phase 5 (Route facade) |
| **W4–W5** | Phase 6 (Dual-path / stream parity) — nur wenn stabil |
| **später** | Phase 7 Moves |

Puffer: Regression / gnom real use. **Lieber eine Woche Pause mit grünem Main als zwei Phasen parallel.**

---

## 8. Kommunikations- & PR-Konventionen

```text
branch:  refactor/phase-1-entry-pipeline
         refactor/phase-2-decision
         ...

commit:  refactor(gateway): split gateway_call into named stages
         test(gateway): cover deny packaging helper

PR body:
  ## Phase N
  ## In scope
  ## Out of scope
  ## Test plan
  ## Risk
```

**Review-Checklist (Architect):**
- [ ] Kein neuer Cross-Import Protect ↔ Route falsch herum  
- [ ] Prove nutzt Production-Path  
- [ ] Fail-closed Semantik erhalten  
- [ ] Diff &lt; ~400 LOC ideal (Phase 1–2), sonst splitten  

---

## 9. Erste Ticket-Backlog (copy-paste)

| ID | Titel | Phase | Priority | Status |
|----|--------|-------|----------|--------|
| M0 | Freeze features; API freeze; plan approved | 0 | P0 | **DONE** |
| M1 | Split `gateway_call` into named stages | 1 | P0 | **DONE** |
| M1b | Extract `build_deny_response` helper | 1 | P0 | **DONE** (`protect.package_deny`) |
| M2 | Introduce `Decision` type + map admits | 2 | P1 | **DONE** |
| M3 | `prove.availability` facade; entry/router use it | 3 | P1 | **DONE** |
| M3b | Chaos test uses production `route` only | 3 | P1 | **DONE** (`select_route`) |
| M4 | `protect` package facade + re-exports | 4 | P2 | **DONE** |
| M5 | `route` package facade; no protect←route cycle | 5 | P2 | **DONE** |
| M6 | Unify stream vs non-stream protect path | 6 | P1 | **DONE** |
| M7 | Axis packages (light facades, no Big-Bang) | 7 | P3 | **DONE** |

---

## 10. Go / No-Go für „Phase 1 starten“

**Go wenn:**
- Product bestätigt: keine Features parallel  
- Builder kennt Scope (nur entry, keine Moves)  
- CI / lokal pytest lauffähig  

**No-Go wenn:**
- Parallele Feature-PR auf gateway/openai_compat  
- „Gleich noch free_llm + dashboard + org layer“  

---

## 11. Abschluss (2026-08-13)

| Phase | Status |
|-------|--------|
| 0 Freeze & Vertrag | DONE |
| 1 entry pipeline stages | DONE |
| 2 Decision | DONE |
| 3 Prove facade | DONE |
| 4 Protect facade | DONE |
| 5 Route facade | DONE |
| 6 Dual-path stream/gateway | DONE |
| 7 Axis packages (light) | DONE (facades; no Big-Bang moves) |

**Regression:** `pytest` 181 green · E2E script **13/13** · Report `docs/E2E_REPORT_2026-08-13.md`.

**Builder scope for Phases 0–7 closed.**

**Architect follow-up (2026-08-13):** system is modular *enough* to use, not cleanly enough decoupled for long-term growth of `service`/`router`/`entry`.  
→ **No big rewrite.** Pain-driven thin slices only:  
[`docs/ARCHITECT_ASSESSMENT_2026-08-13.md`](./ARCHITECT_ASSESSMENT_2026-08-13.md)

Suggested later tickets (Owner go/no-go):

| ID | Slice | Priority | Status |
|----|--------|----------|--------|
| M8 | `route()` vs `execute_routed()` documented + RouteDecision type | P2 | **DONE enough** (separate fns; Prove can route-only) |
| M9 | KeysService → `provider_ops` registry | P2 | **DONE** (maps out of service; adapter Protocol stub) |
| M10 | FreePolicy single “may spend $?” | P1 | **DONE** (`protect.free_policy`) |
| M11 | soft_fail observability helper (no bare pass) | P2 | **DONE** (`soft_fail` in entry stages) |
| R1 | Code revive (team) — extraction leftovers + fail-closed disk | P1 | **DONE** 2026-08-13 · see `CODE_REVIVE_2026-08-13.md` |
| M6b | Stream uses entry prove/admit/rates stages (no second protect brain) | P1 | **DONE** |

### R1 Architect check (team close)

| Check | Result |
|-------|--------|
| Protect ↛ Route / router / failover | pass (`test_no_protect_imports_route`) |
| Public API (`gateway_call`, admit, `/v1`) | unchanged; additive fields only (`product_doc`, `corrupt`) |
| Admit **decisions** | untouched (alert wrappers only) |
| Fail-closed product rule | consumers / keys_app / circuits / ledger / rates |
| Prove still uses production route | unchanged (`select_route`) |
| No adapter zoo / no entry.py split | held |

**Next:** pain-driven only. No R2 unless a real desk break. Owner go/no-go per slice.

---

*Dieser Plan ist die Team-Vereinbarung. Abweichungen = neuer Plan-Abschnitt, kein stilles Scope-Creep.*
