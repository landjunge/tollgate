# FAILURES.md — adversarial E2E (no fixes applied)

**Date:** 2026-08-13  
**Rule:** record only. Do not change product behavior to please a test.  
**Code under test:** `980c6db` on `main` (plus uncommitted `test_free_llm_scope_no_route_when_only_paid_ready` — test only)  
**Client:** gnom-hub-v1 `3.10.1` at `:8080`  
**Gate:** Tollgate `1.0.12` at `127.0.0.1:8787`  
**Data:** `TOLLGATE_HOME=/Users/landjunge/WS-gnom-hub-v1`  
**Auth mode on desk:** **open** (`required=false`, `consumers_n=0`)

Harness: `./scripts/e2e-gnom-hub.sh all` → **13 pass / 0 fail**.

This file is the input for a human triage: **bug vs design vs wrong test expectation**.

---

## Scoreboard

| ID | Scenario | Result | Class |
|----|----------|--------|--------|
| F-001 | Normal OpenAI-compatible chat | **PASS** | — |
| F-002 | Streaming SSE | **PASS** | — |
| F-003 | Tool call (`tool_calls_est=1`) | **PASS** | — |
| F-004 | Tool loop (`tool_calls_est=99`) | **PASS** | — |
| F-005 | Budget exhaustion | **PASS** | — |
| F-006 | Rate limits (RPM) | **PASS** | — |
| F-007 | Provider timeout → clean error | **INCOMPLETE** | see below |
| F-008 | Provider failure + failover | **PASS** | — |
| F-009 | Provider recovery | **PASS** | — |
| F-010 | Tollgate restart | **PASS** | — |
| F-011 | Corrupt `keys_app.json` | **PASS** (unit, isolated home) | not run on live desk |
| F-012 | Corrupt `consumers.json` | **PASS** (unit, isolated home) | not run on live desk |
| F-013 | Auth failures | **PASS** isolated / **N/A** live open mode | see below |
| F-014 | `free_llm` with free providers down | **PASS** | — |
| F-015 | Concurrent requests | **PASS** | — |
| F-016 | Audit write failure | **PASS** (request still served) | — |
| F-017 | Metrics scrape | **PASS** live | — |
| F-018 | Gnom `/api/chat` via Tollgate | **PASS** (job done) | note: Gnom JSON |
| F-019 | Scope `allowed_intents=[free_llm]` + only paid ready | **PASS** (unit) | — |

**Confirmed product FAIL (wrong vs documented safety semantics): none.**

---

## Recorded items (full cards)

Only items that are not a clean PASS, or that need a human call.

### F-007 — Provider timeout does not produce a 2s error envelope

1. **Reproduction**
   ```bash
   curl --max-time 2 -sS http://127.0.0.1:8787/v1/chat/completions \
     -H "Authorization: Bearer gnom" -H "Content-Type: application/json" \
     -d '{"model":"tollgate/free","messages":[{"role":"user","content":"timeout probe"}],"max_tokens":8}'
   ```
2. **Expected (by the adversarial prompt)**  
   Tollgate returns a structured error (`PROVIDER_DOWN` / timeout class) before the client gives up.
3. **Actual**
   ```text
   curl: (28) Operation timed out after 2004 milliseconds with 0 bytes received
   http=000
   ```
   No JSON, no SSE, no `X-Tollgate-*` headers. A 30s client wait **does** return a normal completion (`real ~1.24s` on a later probe).
4. **Logs**  
   No Tollgate error line for this cut — the hop is still inside `urllib` `timeout=120.0` (`chat_stream.iter_sse_json`, `deepseek.chat`, `opencode_zen.chat`).
5. **Severity:** **medium** as production hang risk; **low** as a regression vs current docs (hop timeout is 120s).
6. **Suspected root cause:** There is **no first-byte / request deadline** shorter than 120s. The 2s expectation is **not** a documented Tollgate contract. Chaos covers *injected down*, not *slow TTFB*.

**Triage hint:** likely **wrong test expectation** unless product now wants a shorter hop SLA. Do not “fix” by shrinking the test timeout and calling it green.

---

### F-013 — Live garbage Bearer is not 401 (open mode)

1. **Reproduction (live desk)**
   ```bash
   curl -sS -o /dev/null -w "%{http_code}\n" \
     http://127.0.0.1:8787/v1/health -H "Authorization: Bearer totally-wrong"
   ```
2. **Expected (by a “auth failures” checklist)** `401/403`.
3. **Actual** `200`. Open mode treats the token as a **consumer label**.
4. **Logs** `GET /v1/health` → `auth.required=false`, `consumers_n=0`.
5. **Severity:** **info** on this desk; **high** if this process is ever bound off localhost without consumers.
6. **Suspected root cause:** Documented desk default (`docs/SECURITY.md`, doctor `auth_open`). Isolated TestClient with `consumer-add desk` → **401** missing secret, **401** bad secret, **200** good secret.

**Triage hint:** **design**, not a Protect regression. Isolated auth path matches the documented contract.

---

### F-018 note — Gnom job JSON is not strict JSON

1. **Reproduction**
   ```bash
   curl -sS http://127.0.0.1:8080/api/jobs/<id> | python3 -c "import sys,json; json.load(sys.stdin)"
   ```
2. **Expected** parseable JSON status (`done` / `error`).
3. **Actual** `json.decoder.JSONDecodeError: Invalid control character`. Job **did** finish (`"status":"done"` visible in the raw body). The e2e harness already strips `ord(c)<32`.
4. **Logs** Gnom job `ffefe9f1be2a` brainstorm done; Tollgate audit still receiving `usage` rows.
5. **Severity:** **low** for Tollgate; **medium** for Gnom clients that use strict `json.loads`.
6. **Suspected root cause:** Gnom snapshot/notes embed raw control characters. **Not a Tollgate admit/route fail.**

**Triage hint:** Gnom (or test harness), not Tollgate. Do not change Tollgate error shapes to hide this.

---

## Clean PASSes (short)

| ID | What we saw |
|----|-------------|
| F-001 | `/v1/chat/completions` → `choices`, model `deepseek-v4-flash-free` |
| F-002 | `stream:true` → `data: {chat.completion.chunk}` |
| F-003 | `/v1/invoke` zen chat `tool_calls_est=1` → `ok:true` |
| F-004 | `tool_calls_est=99` → `BLOCKED` / `max_tool_calls` |
| F-005 | `max_usd_day=0.0001` → BLOCKED; envelope restored |
| F-006 | 16 parallel invoke, `max_requests_minute=8` → later `BUDGET_HARD` `9/8` |
| F-008 | `tollgate chaos test deepseek --intent free_llm` → hops on `opencode_zen` |
| F-009 | chat after chaos still `choices` |
| F-010 | kill listen PID → restart uvicorn → chat + `keys_app.json` still has `gnom` |
| F-011/12 | isolated corrupt files fail-closed (freeze / auth). **Not** executed against live `WS-gnom-hub-v1` |
| F-014 | live `/v1/route` `intent=free_llm` → `free_only=true`, winner `opencode_zen`, not deepseek/google; unit spillover tests green |
| F-015 | same as F-006 |
| F-016 | `audit.jsonl` replaced by a directory; chat still returned `choices`; file restored |
| F-017 | live `GET /metrics` 200, `tollgate_up 1` (4304 bytes). Isolated auth-on TestClient correctly 401’d `/metrics` |
| F-018 | Gnom job `72259e21d0c6` (harness) and `ffefe9f1be2a` (manual) **done** |
| F-019 | `test_free_llm_scope_no_route_when_only_paid_ready` — no paid route; `intent=llm` → `protection=scope` |

---

## Proposed fixes (not applied)

Decide per item before any code.

1. **F-007 (only if you want a hang SLA)**  
   Add an **explicit** hop/first-byte deadline (config, default still generous) and map it to `PROVIDER_DOWN` / human message.  
   **Do not** change this just because `curl --max-time 2` failed. That test is stricter than the 120s hop timeout.

2. **F-013 (only if this desk is treated as shared)**  
   `tollgate consumer-add` + bind stay `127.0.0.1`. No semantic change to open mode.

3. **F-018**  
   Fix in **gnom-hub-v1** (strict JSON / sanitize notes), or keep the harness sanitizer. Not a Tollgate patch.

4. **Corrupt-file tests on live desk**  
   Stay isolated. Running them on `WS-gnom-hub-v1` would freeze/lock the real desk on purpose.

---

## Decision log (empty — owner)

| ID | Bug | Design | Wrong expectation | Fix now? |
|----|-----|--------|-------------------|----------|
| F-007 | | ? | ? | no |
| F-013 | | ? | ? | no |
| F-018 | | ? | ? | no (Gnom) |
