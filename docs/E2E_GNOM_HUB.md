# E2E: gnom-hub-v1 → Tollgate (real stack)

**Goal:** Use a real project, not a toy agent. Observe **gnom-hub** as the user — Tollgate should be almost invisible until it protects.

```text
gnom-hub-v1
      │
      ▼
   Tollgate   (HTTP: TOLLGATE_URL  or in-process)
      │
 ┌────┼────┐
 ▼    ▼    ▼
LLM  Tools  Provider
```

---

## Wiring (already in gnom-hub)

| Env | Effect |
|-----|--------|
| `GNOM_TOLLGATE_LLM=1` | default — chat goes through Tollgate |
| `TOLLGATE_URL=http://127.0.0.1:8787` | **HTTP** mode (separate process, real proxy) |
| `TOLLGATE_CONSUMER=gnom` | consumer lane (open mode label) |
| `TOLLGATE_HOME=~/.tollgate` | shared data (or GNOM_WS) |
| `GNOM_TOLLGATE_LLM=0` | opt out (legacy DeepSeek only) |

**Recommended for this protocol:** HTTP mode so Tollgate restart and dashboard are real.

```bash
# Terminal A — Tollgate
cd ~/tollgate
export HOST=127.0.0.1 PORT=8787
.venv/bin/tollgate serve

# Terminal B — optional: set gnom lane budget tight for tests
cd ~/tollgate
.venv/bin/python -m tollgate.cli consumer-budget gnom \
  --max-usd-day 2 --max-tool-calls 20 --allow-intent free_llm --allow-intent llm --allow-op chat

# Terminal C — Gnom-Hub
cd ~/gnom-hub-v1
export TOLLGATE_URL=http://127.0.0.1:8787
export TOLLGATE_CONSUMER=gnom
export GNOM_TOLLGATE_LLM=1
# start hub as you usually do (README)
```

Dashboard: http://127.0.0.1:8787/dashboard  
Expect lane **gnom** (and `gnom:*` agent ids in meta).

---

## Observation rule

While testing, **do not** stare at Tollgate logs first.

Watch **gnom-hub**:

> Do I even notice Tollgate is there?

- Happy path → almost **no**.  
- Protect/Route event → **yes**: clear human error, app still usable.

Collect friction. **Do not fix immediately** — write it under Findings.

---

## Test protocol (checkboxes)

### Test 1 — Normal

- [x] Chat from gnom-hub works  
- [x] Answer returns  
- [x] Tollgate audit/usage shows activity for `gnom`  
- [x] User barely notices proxy  

**Command smoke (optional):**

```bash
./scripts/e2e-gnom-hub.sh normal
```

### Test 2 — Budget

```bash
tollgate consumer-budget gnom --max-usd-day 0.01 --max-tool-calls 50
# generate spend or force high estimate until block
```

- [x] gnom-hub shows **BudgetExceededError** / clear human text  
- [x] Not a raw stack dump  
- [x] Audit: `admit_deny` for gnom  
- [x] Dashboard “What Tollgate prevented” / Today updates  

### Test 3 — Provider failure / failover

- [x] Break primary (wrong key / disable / chaos inject)  
- [x] gnom-hub still gets an answer via fallback **or** clear “unavailable” human message  
- [x] Headers/audit show failover when applicable  
- [x] `tollgate chaos test <primary>` when ≥2 providers  

### Test 4 — Agent loop

```bash
# via invoke or chat with tool_calls_est
curl -s http://127.0.0.1:8787/v1/invoke \
  -H 'Content-Type: application/json' \
  -H 'X-Consumer-Key: gnom' \
  -d '{"provider":"opencode_zen","op":"chat","tool_calls_est":99,"tokens_est":10,"arguments":{"message":"loop"},"agent_id":"gnom:loop"}'
```

- [x] BLOCKED with human tool-loop text  
- [x] gnom path that passes `tool_calls_est` would surface BudgetExceededError  

### Test 5 — Restart

- [x] Kill Tollgate process  
- [x] gnom-hub: temporary failure (acceptable)  
- [x] Restart Tollgate  
- [x] gnom-hub works again without reconfigure  
- [x] Config under `$TOLLGATE_HOME` intact (`consumer-budget`, keys)  

---

## Findings log (fill while testing)

| # | Observed in gnom-hub | Tollgate side | Keep / fix later |
|---|----------------------|---------------|------------------|
| 1 | | | |
| 2 | | | |

**Decision question after a week:**

> Would I leave Tollgate running in front of gnom-hub tomorrow?

---

## Automation

```bash
# From tollgate repo — starts checks against running Tollgate
./scripts/e2e-gnom-hub.sh
```

Does **not** replace manual gnom UI observation — it only proves the pipe.
