# Independent review — Tollgate Control Room & product (2026-08-12)

**Stance:** Do **not** rebuild the WebUI. Test + polish. Product is further along than promo work suggested.

**Sources:** `src/tollgate/dashboard_html.py` (~990 LOC SPA), `server_v1.py`, `control_plane.py`, `certificate.py`, `freeze.py`, README, tests (`157 passed`).

**Leitfrage Overview (already in code):**  
> Is your AI safe, does it work, and what must you do?

---

## Executive summary

| Area | Verdict |
|------|---------|
| Product positioning | 🟢 Strong (Protect · Route · Prove, wedge vs LiteLLM) |
| Control Room architecture | 🟢 Right screens, right metaphors |
| Prove pillar | 🟢 Differentiator — strengthen UX, not rewrite |
| First-run / demo | 🟠 Onboarding + loop test exist; not yet a guided “See it in action” story |
| Value visibility (“what we prevented”) | 🟠 Partial in attention; not emotional on Overview |
| Language consistency (README / UI / site) | 🟠 Drift (PRP vs Reliability ring vs marketing) |
| Security defaults (open mode) | 🔴 Must be crystal-clear for non-localhost bind |
| Name “Tollgate” | 🟢 **Keep** (decided 2026-08-12) — disambiguate in copy/FAQ, no rename |
| Tests | 🟢 157 green unit/contract suite |
| Feature thrash risk | ⚪ Stop adding surfaces; polish the five screens |

---

## What already exists (fact check)

| Claim | In code? |
|-------|----------|
| Control Room, not config cemetery | ✅ Module docstring + footer |
| Screens Overview · Agents · Providers · Prove · Audit | ✅ |
| Reliability score ring + grade | ✅ |
| Needs attention + Recommendations | ✅ |
| Cost split, provider glance | ✅ |
| Agents = who is protected / burns $ / limits | ✅ sub copy + list |
| Prove = resilient or only configured | ✅ |
| 4-step onboarding | ✅ `#onboard` |
| Test tool-loop block | ✅ `btnLoopTest` |
| Unfreeze, API key field | ✅ |
| Chaos test + certificate | ✅ |
| Cold path / certificate CLI | ✅ README + `ten-minute.sh` |

**Conclusion:** Previous “build a WebUI” ideas largely describe **v1.0.12 reality**. Next work = **test + polish**, not greenfield.

---

## 🔴 Must fix

### R1 — Open mode + dashboard attack surface
- Dashboard is unauthenticated HTML; ops APIs use `_require()` which in **open mode** accepts any consumer label.
- **Admin** actions (`POST /v1/freeze`, chaos when auth mode, config write) are gated with `need_admin` only when auth is on.
- **Risk:** Binding `0.0.0.0` + open mode = remote freeze/chaos/config if reachable.
- **Fix:** Default bind localhost; banner on dashboard when `auth.required=false` + non-loopback; refuse admin writes in open mode unless `TOLLGATE_OPEN_ADMIN=1` (or force auth for mutating routes).

### R2 — Name / discoverability collision
- Product is real; brand “Tollgate” fights OpenTollGate, PyPI `tollgate`, enterprise “AI tollgate” metaphor.
- **Fix:** Keep code path short-term; public brand → unique name (decision open: harddeny / admitlane / …). Align netzwerkpunkt + README + UI string once chosen.

### R3 — Prove default provider can mislead first run
- UI hardcodes chaos provider `opencode_zen`. Cold path / free_llm desk often has different keys.
- **Risk:** First “Run test” fails for reasons that look like product failure.
- **Fix:** Default provider from `control` snapshot (first healthy or configured free_llm primary); empty state = “add 2nd key” CTA not red FAIL noise.

### R4 — Language split confuses the one story
| Surface | Language |
|---------|----------|
| README / product | Protect · Route · Prove |
| Overview ring | “AI Reliability” + grade |
| Website (github.io) | Protect your AI agents… |
| Networkpunkt | Agent Safety Layer |

- **Fix:** One glossary in UI chrome: subtitle always `Protect · Route · Prove`; map ring to **Prove score** or **Reliability (Prove)**; Overview headline can stay the operator question.

---

## 🟠 Should improve

### O1 — “Tollgate protected you” (value panel)
- Attention already mentions protection stops (`control_plane` message pattern).
- Missing Overview **hero-adjacent** card: loops stopped · failovers · $ prevented · denies today.
- **Fix:** Aggregate from audit/ledger into `control_snapshot.protection_summary`; render under stats.

### O2 — Guided “See protection in action” (not just one button)
Exists: `Test tool-loop block`.  
Missing: 3-beat demo flow:

1. Simulate agent loop → 🛑 BLOCKED  
2. Simulate provider failure → failover / clear next step  
3. Generate certificate → Prove scorecard  

Put entry on Overview + first visit to Prove (“configured but never tested?”).

### O3 — First-visit Prove empty state
Copy should match:

```text
Your protection is configured.
But has it ever been tested?
[ Run first test ]
```

Today: resilience score + chaos form + NOT_RUN note — good bones, weaker psychology.

### O4 — First success path naming
Onboarding exists; rename CTAs mentally to:
1. **Protect my first agent** (envelope / onboard)
2. **Prove my setup** (loop test or chaos)

Skip → still leave Overview primary CTAs.

### O5 — Dashboard maintainability
- Single giant HTML string: hard to review/diff.
- **Later:** split CSS/JS assets or generate from templates — not urgent for product truth.

### O6 — Agents edit path
- Expand-row detail good; ensure “edit protection” never becomes full config cemetery (keep limits short: budget, max_tool_calls, freeze per consumer if any).

### O7 — Public sites vs product
- netzwerkpunkt.de + github.io sell the product; dashboard is the product body.
- Cross-link: after cold path, open `/dashboard` as primary Aha (already in scripts).

---

## 🟢 Already good

| Item | Why |
|------|-----|
| Screen model | Overview / Agents / Providers / Prove / Audit — complete ops story |
| Agents metaphor | Observed/protected objects, not “configure agents” |
| Prove framing | Differentiates from gateway/monitoring UIs |
| Fail-closed freeze | Admit path fails closed if freeze check errors |
| Certificate / chaos / demo CLI | Real Prove pillar, not slides |
| Cold path honesty | Protect without keys; Prove needs keys called out |
| Recommendations | Actionable, hash-links to Prove |
| Tests | 157 passing — solid regression base for polish |
| Wedge | LiteLLM connects; Tollgate keeps agents in line |
| Footer / help links | Docs DE+EN from Control Room |

---

## ⚪ Cut / do not do now

| Idea | Why cut |
|------|---------|
| Rebuild WebUI from scratch | Waste; product already there |
| Multi-tenant SaaS UI | Off positioning (self-hosted safety layer) |
| Full agent IDE / chat inside dashboard | Wrong product; Gnom-Hub is the desk |
| Config cemetery (every JSON knob) | Explicitly rejected in product voice |
| More marketing surfaces without cold-path/UI polish | Discovery ≠ product truth |
| Dual parallel “Safe · Working · Action” taxonomy | Merge into PRP instead of inventing third |

---

## Priority polish order (max 4 product UI moves)

Aligned with the product note you wrote:

1. **Unify language** → PRP everywhere in dashboard chrome + ring label  
2. **First success CTAs** → Protect first agent · Prove my setup (onboard + Overview)  
3. **Protected-you panel** on Overview  
4. **Demo mode** 3-step flow (loop → failover → certificate)

Then: open-mode security hard rules, Prove provider default, brand rename.

---

## Suggested stop-rule

> If the 10-minute path + dashboard first session is confusing, **stop shipping features** — fix the path.  
(README already says this. Enforce it.)

---

## Relation to Netzwerkpunkt

- **netzwerkpunkt.de** = public hub + Leistungen + browser demos (marketing + lead).  
- **`/dashboard` on :8787** = real product Control Room.  
- Browser demos on netzwerkpunkt are educational; Control Room is authoritative.

Do not rebuild either into the other — **align language and CTAs**.

---

*Reviewer mode: independent pass over current main (v1.0.12). Next implement step = polish list above, not new pillars.*
