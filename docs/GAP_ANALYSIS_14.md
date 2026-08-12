# Gap analysis — 14 product priorities (reviewer checklist)

**Stand:** 2026-08-12 · Repo `landjunge/tollgate` (v1.0.x Core)  
**Stance:** No new feature invention. Score what exists vs the conversion path.

Legend:

| | |
|--|--|
| 🟢 | Done enough for Core conversion |
| 🟡 | Partial — works but friction / polish gap |
| 🔴 | Missing or too weak for “would I run this myself?” |

---

## Scoreboard

| # | Priority | Score | One-liner |
|---|----------|-------|-----------|
| 1 | First 10 minutes | 🟡 | `ten-minute.sh` + dashboard open exist; still multi-step clone/venv |
| 2 | Existing app → Tollgate | 🟡→🟢 | Drop-in + **Dashboard Connect snippet** (Python/curl/env + Copy) |
| 3 | Agent auto-discovery | 🟡→🟢 | Open mode + **New agents** panel + Protect this agent CTA |
| 4 | Good defaults | 🟢 | `_default` envelopes ship Protect-on |
| 5 | “What it prevented” | 🟡 | `protection_summary` + Overview panel; $ prevented still soft |
| 6 | Prove must work | 🟡→🟢 | **Prove my setup** runs loop + chaos + certificate suite |
| 7 | Human errors | 🟡→🟢 | `human` on block cards + OpenAI error.message + X-Tollgate-Human |
| 8 | Activity timeline | 🟡→🟢 | Overview **Today** feed from denies / prove / budget |
| 9 | Config export/backup | 🟢 | `tollgate snapshot export/import` + tests |
| 10 | Security audit | 🟡→🟢 | **docs/SECURITY.md** + doctor production_readiness (formal pen-test still optional) |
| 11 | Scenario tests | 🟡→🟢 | **tests/test_scenarios_core.py** (B/C/D + human circuit) |
| 12 | Docs → three pages | 🔴→🟡 | Entry trio: QUICKSTART · HOW_IT_WORKS · PRODUCTION_CHECKLIST (rest advanced) |
| 13 | Production mode | 🔴→🟡 | **production_readiness %** in `tollgate doctor` (no hard PROD flag yet) |
| 14 | Stop more breadth | 🟢 | North star: conversion only; name kept |

**Overall:** Core product is **real**. Gaps are almost all **path + proof + trust**, not missing pillars.

---

## 1. First 10 minutes — 🟡

**Have**

- `./scripts/ten-minute.sh` → demo protect + optional chaos + certificate + opens dashboard  
- `docs/TEN_MINUTE.md` stranger checklist  
- Dashboard first-success strip (Protect / Prove / Demo)

**Gap**

- Still: clone + venv + pip + script (not “one binary”)  
- Chaos Prove often NOT_RUN without keys — story OK if copy is clear  
- Auto-open dashboard is macOS-friendly; CI/headless needs `OPEN_DASHBOARD=0`

**Change (if any)**  
Harden only where strangers fail — don’t add features. Measure: unattended run by a friend.

---

## 2. Existing app → Tollgate — 🟡

**Have**

```text
OPENAI_BASE_URL=http://127.0.0.1:8787/v1
OPENAI_API_KEY=<lane-label>   # open mode
```

- `docs/OPENAI.md` Python / curl / Node patterns  
- OpenAI + Anthropic drop-ins live

**Gap**

- **No** Control-Room / site “Copy snippet” generator (Python/Node/curl tabs)  
- Port is **8787**, not 8000 — docs must be consistent (never invent 8000)  
- `tool_calls_est` still best-effort from history — loops need awareness

**Change**  
One copy box in dashboard Overview or site Quickstart — **not** more blog posts.

---

## 3. Agent auto-discovery — 🟡

**Have**

- Open mode: any `Authorization: Bearer <label>` becomes consumer id  
- Lanes show up in Control Room after traffic / budget set  
- Onboarding can create named lane + limits

**Gap**

- No explicit UI: **“New agent detected → Protect this agent”**  
- User can still confuse consumer label vs secret auth mode  
- Scopes remain advanced (good) but invisible discovery moment is weak

**Change**  
On control snapshot: flag consumers first-seen / unprotected → Overview CTA. Small UX, high conversion.

---

## 4. Defaults — 🟢

**Have** (`app_config` `_default`):

| Dim | Default |
|-----|---------|
| max_usd_day | 5 |
| max_usd_request | 0.5 |
| max_usd_hour | 2 |
| max_requests_minute | 60 |
| max_tool_calls | 25 |
| auto_failover | on (routing config) |

**Gap**

- First-run copy doesn’t always **surface** these numbers in UI as “already on”  
- Demo script uses its own $2/day/20 tools — fine for Aha

**Change**  
Show “Protection already on for unknown lanes” chip once; no config cemetery.

---

## 5. See that Tollgate does something — 🟡

**Have**

- Overview: agent stops, denies, protection_summary panel  
- Attention: “N agent protection stop(s)…”  
- Block modal after loop test  

**Gap**

- **$ protected** is not rigorously computed (would need counterfactual)  
- Rate-limit hits not always broken out as their own counter  
- Panel empty until first real deny — demo mode fills the gap

**Change**  
Keep panel; optional: count by protection type from audit. Don’t invent fake $ saved.

---

## 6. Prove — 🟡

**Have**

- `tollgate chaos test`, certificate scorecard, Dashboard Prove tab  
- Certificate checks: budget / loop / failover statuses  
- Guided “See protection in action” + Prove first-visit CTA  

**Gap**

- Not a **single** button that runs full suite: budget + tools + failover + circuit + recovery  
- Failover still needs ≥2 providers + keys  
- Resilience score ≠ “TOLLGATE VERIFIED” marketing card (close via certificate)

**Change**  
`Prove my setup` orchestrator: always run loop test; chaos if ready; always refresh certificate. Mostly UI glue.

---

## 7. Human errors — 🟡

**Have**

- `block_view.build_block_card` → paste-friendly 🛑 REQUEST BLOCKED  
- Freeze / budget / tool reasons structured  

**Gap**

- Failover path / 503 OpenAI-compat errors not always:  
  *“OpenAI unavailable; switched to Anthropic.”*  
- Circuit open messages can still feel raw  

**Change**  
Map top 5 provider/circuit errors to one-line operator English on chat/invoke responses.

---

## 8. Activity timeline — 🟡

**Have**

- Audit screen (events table)  
- `recent_denies` in control plane  
- CLI `tollgate audit`  

**Gap**

- Not a **TODAY** reverse-chron feed on Overview  
- No emoji story line (loop / failover / budget 80%)

**Change**  
Overview section “Today” from last N audit rows — reuse audit, don’t build analytics.

---

## 9. Config export / backup — 🟢

**Have**

- `tollgate snapshot export|import|info`  
- Tests: `tests/test_snapshot.py`  
- Optional include keys / omit audit  

**Gap**

- Dashboard button “Export config” missing (CLI is enough for Core if documented)  
- Not YAML by default (`.tgz` ops snapshot) — OK if documented  

**Change**  
One ghost button → download snapshot or show CLI. Low priority vs path.

---

## 10. Security audit — 🟡

**Have**

- Fail-closed freeze, ledger fail-closed tests  
- Metrics auth modes, open-mode banner, localhost default bind  
- Audit without secrets in dashboard copy  
- Snapshot keys opt-in  

**Gap**

- No written **SECURITY.md checklist pass** with dated sign-off  
- Webhooks / CORS / SSRF / management rate limits not systematically verified in this review  
- Multi-worker caveats documented in STABILITY.md  

**Change**  
Before “real users”: dedicated security pass doc + fix list. **Must before serious production.**

---

## 11. Scenario tests — 🟡

**Have**

- `test_chaos_resilience`, `test_failover`, `test_tool_calls_protect`,  
  `test_ledger_fail_closed_chain`, `test_freeze_circuits`, `test_contract_v1`, concurrency  

**Gap**

- Not named as Scenario A–D in one suite  
- Restart → config survives: partial (paths/portable tests)  
- UI update after budget: not E2E browser  

**Change**  
Add `tests/test_scenarios_core.py` that chains existing helpers under Scenario labels — thin wrapper.

---

## 12. Docs → three pages — 🔴

**Have**

- TEN_MINUTE, GETTING_STARTED, USER_GUIDE, HILFE, FAQ, OPENAI, DEMO, …  
- **~27 markdown files, thousands of lines**

**Gap**

- Not reduced to **Quickstart / How it works / Production checklist**  
- Density confuses strangers  

**Change**  
Three **entry** docs as the only homepage links; rest archive/advanced. Don’t delete knowledge — **gate** it.

Suggested:

1. `docs/QUICKSTART.md` (5 min protect) — or promote TEN_MINUTE  
2. `docs/HOW_IT_WORKS.md` — Protect · Route · Prove  
3. `docs/PRODUCTION_CHECKLIST.md` — before prod  

---

## 13. Production mode — 🔴

**Have**

- doctor, certificate, freeze, STABILITY notes  

**Gap**

- No `DEVELOPMENT` vs `PRODUCTION` mode flag  
- No readiness % panel  

**Change**  
Later: `tollgate doctor --production` or dashboard “Production readiness” from existing checks. **After** one real user, not before.

---

## 14. What not to build — 🟢 (process)

Aligned: no more provider sprawl, marketing SEO, fancy charts, Organization layer until Core conversion proven.

---

## If I took over the project tomorrow

Exact order (matches your list, with current scores):

```text
1. 🔴 First-run / onboarding test (stranger)     — validate path
2. 🔴 Existing OpenAI app attach                 — base_url only
3. 🟡 Agent auto-detect UX                       — “Protect this agent”
4. 🟢 Protection defaults                        — already on; surface them
5. 🟡 Failover real test                         — keys + second provider
6. 🟡 Prove orchestration                        — one button suite
7. 🔴 Security audit pass                        — before non-local users
8. 🟢 Restart/backup                             — snapshot exists; document
9. 🟡 Activity feed                              — Overview TODAY
10. 🟢 Production readiness                      — later
```

Then: **use it for a week** with broken provider, tiny budget, forced loop.

---

## Bottom line

| Question | Answer |
|----------|--------|
| Need more features? | **No.** |
| Need install → protect → prove → daily useful? | **Yes — that’s the whole game.** |
| Is Core already “mächtig”? | **Yes for one operator.** |
| Biggest holes | Docs density, auto-discover UX, human failover errors, security sign-off, prod mode |

**Do not start Organization.**  
**Do not start more SEO.**  
Next code only if a stranger fails a step — then fix that step.
