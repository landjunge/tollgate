# Adversarial E2E — gnom-hub-v1 ↔ Tollgate

**Date:** 2026-08-13  
**Stance:** Feature freeze. No refactor. Record only.  
**Code:** `980c6db` (+ local test `test_free_llm_scope_no_route_when_only_paid_ready`)  
**Stack:** Tollgate `:8787` · Gnom `:8080` · `TOLLGATE_HOME=/Users/landjunge/WS-gnom-hub-v1`  
**Auth:** open mode (`required=false`) — desk default.

```bash
export TOLLGATE_HOME=/Users/landjunge/WS-gnom-hub-v1
export GNOM_URL=http://127.0.0.1:8080
./scripts/e2e-gnom-hub.sh all
```

Harness: **13 / 13 PASS** (same as prior T1–T5 + gnom API + restart).

---

## Matrix

| ID | Test | Result | Evidence |
|----|------|--------|----------|
| E2E-001 | Normal request | **PASS** | `/v1/chat/completions` returned `choices` |
| E2E-002 | Streaming | **PASS** | SSE chunks, model `deepseek-v4-flash-free` |
| E2E-003 | Tool call (est=1) | **PASS** | `/v1/invoke` `ok:true` opencode_zen |
| E2E-004 | Tool loop | **PASS** | `tool_calls_est=99` → BLOCKED `max_tool_calls` |
| E2E-005 | Budget exceeded | **PASS** | tight `max_usd_day` → BLOCKED |
| E2E-006 | Provider down → failover | **PASS** | `chaos test deepseek` → traffic on `opencode_zen` |
| E2E-007 | Provider back / recovery | **PASS** | chat after chaos returned choices |
| E2E-008 | Tollgate restart | **PASS** | kill → uvicorn back → chat + `keys_app.json` intact |
| E2E-009 | Corrupt `keys_app.json` | **PASS** (unit) | `test_corrupt_keys_app_fail_closed_freeze` — not run on live desk |
| E2E-010 | Corrupt `consumers.json` | **PASS** (unit) | `test_corrupt_consumers_json_fail_closed` — not run on live desk |
| E2E-011 | Free provider down → no paid | **PASS** | unit + live `/v1/route` `free_only=true` winner `opencode_zen` |
| E2E-012 | Scope `allowed_intents=[free_llm]` + only paid ready | **PASS** (unit) | new test: `route` none + `routed_chat(intent=llm)` `protection=scope` |
| E2E-013 | Auth wrong | **N/A live / PASS unit** | desk is **open mode** (Bearer label). Isolated: 401 when consumers required (`test_http_auth_gate`) |
| E2E-014 | Audit broken | **PASS** | `audit.jsonl` replaced with a directory; chat still returned choices; file restored |
| E2E-015 | Provider timeout → clean error | **INCOMPLETE** | client `--max-time 2` got curl 28 / 0 bytes — Tollgate did not emit an error envelope in 2s. Not a proven product fail. Failover/chaos covers *down*, not slow-TTFB. |
| E2E-016 | Parallel requests / limits | **PASS** | 16 concurrent invoke, `max_requests_minute=8` → later hops `BUDGET_HARD` `9/8` |
| E2E-017 | Gnom `/api/chat` | **PASS** | job `72259e21d0c6` done |

Unit slice for this matrix: **53 passed** (free_policy, free_llm spillover, scenarios, loop, concurrency, auth, revive, chaos, failover, openai, ledger).

---

## Failures

**None proven on Protect/Route/Prove happy+deny paths.**

### INCOMPLETE — E2E-015 provider timeout

| | |
|--|--|
| **Repro** | `curl --max-time 2` POST `/v1/chat/completions` model `tollgate/free` |
| **Expected** | Tollgate JSON/SSE error (`PROVIDER_DOWN` / timeout class) before the client gives up — or documented proxy timeout |
| **Actual** | `curl: (28) Operation timed out after 2004 milliseconds with 0 bytes received` |
| **Action** | Do **not** refactor yet. Next desk pain: measure first-byte latency and whether uvicorn/upstream holds the socket without a deadline. Only then add a hop timeout if a real gnom hang is seen. |

### Observation — E2E-013 live auth

Desk `auth.required=false`. A garbage Bearer still gets 200 on `/v1/health` (open-mode label). That is **by design** for local desk. Shared/prod needs `consumer-add` — already a doctor warning, not a regression.

---

## FreePolicy (unnegotiable)

```text
free_llm + free providers down
    → MUST NOT select paid
```

`tests/test_free_llm_no_spillover.py` + live `/v1/route` → **PASS** (`opencode_zen`, `free_only=true`, not deepseek/google).

```text
consumer allowed_intents=[free_llm]
paid-only providers ready (deepseek/google stand-ins for OpenAI/Anthropic)
    → NO ROUTE
    → intent=llm is scope deny
```

`test_free_llm_scope_no_route_when_only_paid_ready` → **PASS**.

---

## Product question

> Would I leave Tollgate in front of gnom-hub tomorrow?

**Yes** for this desk. The gap that still hurts the “real-world validation” score is not another module split — it is **slow/hung upstream without a first-byte deadline** (E2E-015) and **open mode on a machine that might be treated as prod**.

No code change from this run except the FreePolicy regression test above.

---

## Related

- Harness: `scripts/e2e-gnom-hub.sh` · protocol `docs/E2E_GNOM_HUB.md`
- Prior T1–T5: `docs/E2E_REPORT_2026-08-13.md`
