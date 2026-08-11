# Tollgate product direction

## Core promise

> **Tollgate prevents AI agents from becoming unreliable, expensive and uncontrollable.**

Not: “access to many LLM providers.”  
Category:

> **The simplest self-hosted AI control plane for agents.**

Sibling products (LiteLLM, Portkey, Helicone, Bifrost, Envoy AI Gateway, Cloudflare AI Gateway) prove the **market** exists. They also prove that **“AI Gateway” alone is crowded**.

Tollgate does **not** win by supporting 30 more providers.

## Competitive map (why not clone LiteLLM)

| Tool | Strength | Tollgate wedge |
|------|----------|----------------|
| **LiteLLM** | 100+ providers, proxy, fallbacks, spend | **Agent protection + policy + MCP/tools**, not catalog width |
| **Portkey** | Production stack, guardrails, governance | **Self-hosted, simpler, developer-first desk** |
| **Helicone** | Observability, cost analytics | **Runtime control**: hard stop before spend, not only after |
| **Bifrost** | Fast OSS gateway | We’re not competing on raw gateway speed |
| **Envoy AI Gateway** | K8s / infra | Desk/agents first, not platform engineering first |
| **Cloudflare AI Gateway** | Managed edge | **Provider-neutral, self-hosted, USB/portable** |

**One-liner vs the field:**

> LiteLLM connects you to models.  
> Helicone shows what happened.  
> **Tollgate keeps your agents from misbehaving.**

## Three pillars (product, not feature soup)

```text
                 TOLLGATE
                    │
       ┌────────────┼────────────┐
       ↓            ↓            ↓
  Reliability     Budget      Policy
       │            │            │
    Failover      $/day      token limits
    Health        $/agent    rate limits
    Circuit       $/request  allowed models
    Ranking       alerts     MCP/tool caps
       └────────────┼────────────┘
                    ↓
             LLM + tools
```

| Pillar | Job |
|--------|-----|
| **Reliability** | Health, circuits, failover, health-aware route |
| **Cost** | Envelopes, burn, projection |
| **Agent protection** | max $/request/hour, rpm, tokens, tool loops — **fail closed** |

MCP + agents (not only chat completions) is a deliberate second surface:

```text
Agent ──► LLM ──► Tollgate ──► providers
   └──► MCP/tools ──► Tollgate ──► APIs
```

Same consumer lane: *this agent may use free LLM, max €5/day, max 20 tool calls per task.*

## What we refuse (for now)

- “Support every provider LiteLLM has”  
- Zapier/Slack/Discord/K8s operator sprawl  
- Cloud multi-tenant SaaS before the safety layer is excellent  

**80% of users never need advanced JSON** — budget + protection + failover.

## 5-minute success

```bash
docker compose up -d
# open http://127.0.0.1:8787/dashboard
# set OPENAI_BASE_URL=http://127.0.0.1:8787/v1
```

Then:

```text
✓ Providers connected (Key.txt)
✓ Budget / agent limits set
✓ Failover on
→ Agents stop burning money in loops
```

## Roadmap phases

| Phase | Focus | Status |
|-------|--------|--------|
| 1 Stability | Config, secrets, doctor, tests | continuous |
| 2 Agent protection | request/hour/minute/tool hard stops | **done** |
| 3 Intelligence | health-aware routing + explain | **done** |
| 4 Visibility | feelable dashboard (spend, health, attention) | **shipping** |
| 5 Enterprise | RBAC, teams, SSO | later |

## Audiences

1. Agent builders / startups  
2. Companies with many AI tools  
3. n8n / automation  
4. Self-hosted + paid APIs  
