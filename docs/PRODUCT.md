# Tollgate product direction

## Core promise (sharp)

> **Tollgate protects your AI applications from provider outages, runaway costs and bad model choices.**

Not “another LLM gateway.” Category line:

> **The safety and control layer for AI agents.**

Existing gateways **route** traffic. Tollgate **protects and governs** AI traffic.

## Why this exists

LLM providers multiply. Agents get more autonomous. That creates three operational failures:

1. **Outages** without controlled failover  
2. **Runaway cost** from loops, bugs, unbounded tools  
3. **Opaque routing** nobody can audit  

Tollgate is the place those problems stop.

## Three product layers

| Layer | Job | User-visible |
|-------|-----|----------------|
| **Reliability** | Health, circuits, failover | Provider scores, auto-failover |
| **Cost intelligence** | Day/hour/request spend by agent | Burn, projection, alerts |
| **Agent protection** | Stop loops before the invoice | Per-request / per-minute / per-hour hard stops |

Everything else (OpenAI/Anthropic drop-ins, MCP, n8n, cache) is **distribution** — not the product story.

## What we are not doing now

- Twenty more integrations (Zapier, Slack, K8s operator, …)  
- Competing with Kong/Envoy/LiteLLM as “more protocols”  
- Enterprise SSO before the safety layer is excellent  

**80% of users should never need advanced JSON.** Simple budgets + protection first.

## Audiences

1. AI-agent builders / startups  
2. Companies with many AI tools / teams  
3. n8n / automation  
4. Self-hosted + paid APIs  

## Roadmap (product phases)

| Phase | Focus | Status |
|-------|--------|--------|
| **1 Stability** | Config back-compat, secrets, tests, doctor | continuous + PR #7 |
| **2 Agent protection** | request/hour/minute/token hard stops | **v0.2.1 shipping** |
| **3 Intelligence** | health-aware smart routing | **v0.2.2** |
| **4 Visibility** | dashboard headlines that sell | mini `/dashboard` exists |
| **5 Enterprise** | RBAC, teams, SSO, admin audit | later |

## Agent protection (killer surface)

Per consumer / agent lane:

```yaml
consumer_envelopes:
  coding-agent:
    max_usd_day: 20
    max_usd_hour: 5
    max_usd_request: 0.50
    max_requests_minute: 30
    max_tokens_request: 20000
    max_tool_calls: 15   # when client sends tool_calls_est
```

On breach: **fail closed** → audit → optional alert. No silent bill.

## Simple config (target UX)

```yaml
# conceptual — advanced keys_app remains available
tollgate:
  budget:
    daily: 50
  reliability:
    failover: true
  routing:
    strategy: cost_optimized   # later
  protection:
    default_max_usd_request: 0.5
```

## Feelable proof

```text
$73 protected · 47 auto failovers · 12 agents under hard limits
```

`/dashboard` · `GET /v1/control` · `tollgate doctor` · `tollgate control`
