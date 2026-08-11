# Demo: “My AI agent must never go out of control”

**Not** an API gateway demo. **Not** multi-LLM catalog shopping.

> **Tollgate is the safety layer between your AI agents and the internet.**

Killer line:

> **My AI agent must never go out of control.**

---

## The story in 30 seconds

```text
Customer Support Agent
        │
        ↓
     Tollgate          ← budgets · tool-loop stops · scopes · freeze
      /    \
     ↓      ↓
   OpenAI  Anthropic   (or Zen / DeepSeek on a local desk)
```

You set hard rules for one **consumer** (agent lane):

| Rule | Example |
|------|---------|
| Max $ per request / day | `$0.50` / `$2` |
| Max tool calls (loop depth) | `20` |
| Max requests / minute | `50` |
| Allowed providers | `openai`, `anthropic` (or desk: `opencode_zen`, `deepseek`) |
| Allowed intents / ops | `llm`, `chat` |
| Failover | automatic if primary dies |
| Panic | `tollgate freeze` |

Then the two things that always happen in production:

1. **Agent bug → tool loop** → Tollgate **blocks** (Protect)  
2. **Provider outage** → Tollgate **fails over** and you can **prove** it (Route + Prove)

---

## Aha #1 — Protect (agent loop)

### Setup (one lane)

```bash
# Support agent lane — concrete, not "unlimited"
tollgate consumer-budget support-agent \
  --max-usd-day 2 \
  --max-usd-request 0.5 \
  --max-requests-minute 50 \
  --max-tool-calls 20 \
  --allow-provider opencode_zen \
  --allow-provider deepseek \
  --allow-intent free_llm \
  --allow-intent llm \
  --allow-op chat

# Optional: open dashboard
open http://127.0.0.1:8787/dashboard
```

### What the agent is allowed to do

```text
✓ spend up to $2 / day on this lane
✓ max ~$0.50 estimated per request
✓ max 20 tool calls this turn (loop depth)
✓ only listed providers / intents / ops
✓ automatic failover when primary is sick
✓ instant stop: tollgate freeze
```

### What happens when the agent bugs

```text
Agent → Tool → LLM → Tool → LLM → Tool → …
                    (loop)
```

Send the same pattern Tollgate already enforces:

```bash
# Invoke path (explicit tool_calls_est = loop depth this turn)
curl -s http://127.0.0.1:8787/v1/invoke \
  -H 'Content-Type: application/json' \
  -H 'X-Consumer-Key: support-agent' \
  -d '{
    "provider": "opencode_zen",
    "op": "chat",
    "arguments": {"message": "hi", "max_tokens": 32},
    "tool_calls_est": 21,
    "agent_id": "support-agent",
    "request_class": "interactive"
  }'
```

Or OpenAI drop-in:

```bash
curl -s http://127.0.0.1:8787/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer support-agent' \
  -d '{
    "model": "tollgate/free",
    "messages": [{"role":"user","content":"hi"}],
    "tool_calls_est": 21
  }'
```

### The Aha screen (what you show)

```text
🛑 REQUEST BLOCKED

Consumer:   support-agent
Reason:     agent protection / max_tool_calls
Tool calls: 21 > 20
Protection: max_tool_calls

# also in audit + dashboard "Recent denies"
tollgate audit --event admit_deny --consumer support-agent
```

OpenAI-shaped body includes `error.tollgate.protection` and headers  
`X-Tollgate-Error-Class` / `X-Tollgate-Protection` for n8n IF-nodes.

**That is the product.** Not “we proxy OpenAI.”

---

## Aha #2 — Prove (provider dies)

```bash
# Simulate primary outage; prove traffic still routes
tollgate chaos test opencode_zen --requests 10
tollgate resilience
```

Narrative:

```text
PRIMARY FAILURE SIMULATION

Provider:     opencode_zen (stand-in for “OpenAI”)
Requests:     10
Primary hit:  0 (skipped while chaos inject active)
Fallback:     next healthy provider in free_llm / llm chain
Survived:     yes / no  (from report)
Recovery:     ms (vs reliability.max_failover_time_s)
```

Dashboard **Prove** panel + `tollgate report`:

> **Your agent survived.**

CTO language without a slide deck.

---

## Homepage copy (minimal)

```text
TOLLGATE

Protect your AI agents
from runaway costs and provider failures.

        [ 5-minute setup → GETTING_STARTED ]
        [ Run the demo  → this file        ]

✓ Budget protection
✓ Agent loop protection
✓ Provider failover
✓ Disaster recovery testing
✓ Audit trail
```

Live pane while demoing:

```text
Your agent: support-agent
  $0.82 spent today
  17 tool calls (of 20)
  primary → healthy
```

Then chaos:

```text
primary
   ↓
💥 OUTAGE
   ↓
→ fallback
→ traffic recovered
```

Then loop:

```text
Agent → Tool → Agent → Tool → …
🛑 BLOCKED  reason: max_tool_calls
```

**Everyone gets it in 30 seconds.**

---

## Positioning (use these words)

| Say this | Not this |
|----------|----------|
| **Tollgate protects AI agents in production.** | “AI Gateway” |
| Safety layer between agents and the internet | Multi-LLM proxy |
| Control cost. Survive provider failures. Prove it works. | Catalog of 100 models |
| Protect · Route · Prove | LiteLLM alternative (as primary frame) |

One-liners:

> **Tollgate is the safety layer between your AI agents and the internet.**

> **Control cost. Survive provider failures. Prove your AI infrastructure works.**

Vs field (keep):

> LiteLLM connects models. Helicone shows traffic.  
> **Tollgate keeps agents in line — and proves failover works.**

---

## Who it’s for (narrow)

### 1. Teams running agents in production
Fear: cost, loops, outages, no audit, no kill switch.

### 2. Agent-framework builders
```text
LangGraph / CrewAI / AutoGen / custom
              ↓
           Tollgate
              ↓
     LLM · MCP · tools
```

### 3. n8n / automation teams
> “What if this workflow agent-loops?”  
> Tollgate stops it — community node + OpenAI `base_url`.

Not: “everyone with an API key.”

---

## Map story → code (already shipped)

| Story beat | Code / surface |
|------------|----------------|
| $ / task / day caps | `consumer_envelopes`, `agent_guard`, `limits.py` |
| Tool loop hard stop | `max_tool_calls`, `tool_calls_est` on invoke/chat |
| Provider / op allowlists | scopes: `allowed_providers` / `allowed_ops` |
| Failover | `failover.py`, health-aware `router.py` |
| Instant stop | `tollgate freeze` |
| Prove outage | `tollgate chaos test`, resilience score, dashboard |
| Who/why blocked | `tollgate audit`, `/v1/audit`, dashboard denies |
| n8n | `n8n-nodes-tollgate`, OpenAI base_url |

The demo is **not invented**. It’s a path through existing features.

---

## Live desk script (copy-paste)

```bash
export TOLLGATE_HOME=${TOLLGATE_HOME:-$HOME/.tollgate}
tollgate doctor
tollgate serve   # other terminal if needed

tollgate consumer-budget support-agent \
  --max-usd-day 2 --max-usd-request 0.5 \
  --max-tool-calls 20 --max-requests-minute 50 \
  --allow-intent free_llm --allow-intent llm --allow-op chat

# Aha 1 — loop blocked (no spend required)
curl -s http://127.0.0.1:8787/v1/invoke \
  -H 'Content-Type: application/json' \
  -H 'X-Consumer-Key: support-agent' \
  -d '{"provider":"opencode_zen","op":"chat","arguments":{"message":"x"},"tool_calls_est":99,"agent_id":"support-agent"}' | jq .

tollgate audit --event admit_deny --limit 5

# Aha 2 — DR
tollgate chaos test opencode_zen --requests 10
tollgate resilience
tollgate status
```

Dashboard: http://127.0.0.1:8787/dashboard  

Full product lock: [PRODUCT.md](PRODUCT.md) · setup: [GETTING_STARTED.md](GETTING_STARTED.md)
