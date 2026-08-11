# Tollgate product direction

## Killer use case

# “My AI agent must never go out of control.”

Not “API gateway.” Not “multi-LLM proxy.”

> **Tollgate is the safety layer between your AI agents and the internet.**

**Product framing:**

> **Tollgate protects AI agents in production.**

**Subtitle:**

> **Control cost. Survive provider failures. Prove your AI infrastructure works.**

**Name / architecture label (still true):**

> **Tollgate — AI Reliability & Control Plane** · Protect · Route · Prove

---

## Why this wedge

LiteLLM is “connect every model.” Helicone is “see the traffic.”  
We win when the pain is:

| Fear | Tollgate answer |
|------|-----------------|
| Runaway agent / tool loop | Pre-admission `max_tool_calls` hard deny |
| Bill shock | Envelopes + $ / request / hour / day |
| Wrong model / provider | Consumer scopes (allow/block) |
| Provider dies at 3am | Health-aware failover |
| “Does DR work?” | Chaos test + resilience score (**Prove**) |
| No kill switch | `tollgate freeze` |
| No forensics | Audit trail + report |

Competitive one-liner (keep):

> LiteLLM connects models. Helicone shows traffic.  
> **Tollgate keeps agents in line — and proves failover works.**

**Do not lead with** “AI Gateway” — that lands you next to LiteLLM on features they own.

---

## Three pillars (map to the demo)

| # | Pillar | Demo beat | Product meaning |
|---|--------|-----------|-----------------|
| **1 Protect** | Agent loop / budget / scopes / freeze | 🛑 REQUEST BLOCKED · `max_tool_calls` | Hard stop before HTTP |
| **2 Route** | Failover when primary dies | traffic → secondary | Health-aware + execute failover |
| **3 Prove** | Chaos + score | “Your agent survived.” | Evidence, not vibes |

Full click-through: **[DEMO.md](DEMO.md)**.

---

## Concrete agent lane (support agent)

```text
Customer Support Agent
        │
        ↓
     Tollgate
      /    \
     ↓      ↓
   primary  fallback
```

Example policy (real knobs in code):

```bash
tollgate consumer-budget support-agent \
  --max-usd-day 2 \
  --max-usd-request 0.5 \
  --max-tool-calls 20 \
  --max-requests-minute 50 \
  --allow-intent free_llm --allow-intent llm \
  --allow-op chat
```

| Allowed | Enforced by |
|---------|-------------|
| Max $ / task-ish (request) | `max_usd_request` |
| Max $ / day | `max_usd_day` |
| Max tool calls / turn | `max_tool_calls` + `tool_calls_est` |
| Max RPM | `max_requests_minute` |
| Only some providers/ops | scopes (`allowed_*` / `blocked_*`) |
| Switch provider on failure | router + failover |
| Stop everything | freeze |

---

## Target audience (narrow)

### 1. Companies running AI agents in production
Cost, loops, outages, control, audit.

### 2. Agent-framework developers
LangGraph, CrewAI, AutoGen, in-house stacks:

```text
Agent framework
       ↓
    Tollgate
       ↓
LLM + MCP + tools
```

### 3. n8n / automation teams
Easiest live story: “What if this workflow agent-loops?” → Tollgate stops it  
(`base_url` + community node).

**Not** primary: “everyone who needs a multi-provider catalog.”

---

## Reliability policy (config)

```json
"reliability": {
  "availability_target": 99.9,
  "max_failover_time_s": 5.0,
  "required_fallbacks": 2,
  "gradual_recovery_s": 60.0
}
```

| Field | Meaning |
|-------|---------|
| `availability_target` | Reported aspirational % (with score) |
| `max_failover_time_s` | Chaos test recovery SLA |
| `required_fallbacks` | Min enabled providers per LLM intent |
| `gradual_recovery_s` | After chaos stop, ramp traffic back (0 = instant) |

## Chaos / DR (Prove)

```bash
tollgate chaos test opencode_zen --requests 10
tollgate resilience
```

Narrative output shape (product language):

```text
FAILOVER / OUTAGE SIMULATION
Primary injected down
Automatic failover   …
Recovery time        …
✓ Application / agent survived …
```

## Resilience Score

```bash
tollgate resilience
# or GET /v1/resilience
```

## Homepage (minimal)

```text
TOLLGATE

Protect your AI agents
from runaway costs and provider failures.

  [ Run the demo → docs/DEMO.md ]
  [ 5-minute setup → GETTING_STARTED.md ]

✓ Budget protection
✓ Agent loop protection
✓ Provider failover
✓ Disaster recovery testing
✓ Audit trail
```

## Business sketch (later)

| Tier | Scope |
|------|--------|
| Community | 1 host, protect/route/prove, freeze, chaos CLI |
| Pro | analytics history, multi-desk, advanced routing |
| Enterprise | RBAC, SSO, multi-region, SLA |

## What we already ship (story → code)

| Story | Shipped |
|-------|---------|
| Protect | envelopes, agent_guard, scopes, freeze, audit, webhooks |
| Route | health router, failover, circuits (disk + jitter + mtime) |
| Prove | chaos, resilience, doctor, dashboard, report |
| Surfaces | OpenAI/Anthropic drop-in, MCP, n8n, portable snapshot |

## What we refuse

- Leading with “gateway / 100 models”  
- Feature soup without Protect · Route · Prove  
- Mixing agent conversation memory into Tollgate (ops only)

## See also

- **[DEMO.md](DEMO.md)** — 30-second + live desk script  
- [GETTING_STARTED.md](GETTING_STARTED.md) · [VISION.md](VISION.md) · [ARCHITECTURE.md](ARCHITECTURE.md)
