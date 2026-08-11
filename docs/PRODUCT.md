# Tollgate product direction

## Core promise

> **Prove that your AI application survives a provider outage — and keep agents from becoming expensive and uncontrollable.**

**Product name framing:**

> **Tollgate — AI Reliability & Control Plane**

Three killer features:

| # | Pillar | Meaning |
|---|--------|---------|
| **1 Protect** | Budget, rate, token, tool-loop hard stops | Agents cannot burn the invoice |
| **2 Route** | Health-aware failover + explain | Traffic moves when providers die |
| **3 Prove** | Chaos / DR tests + Resilience Score | Evidence for CTOs, not just config |

Not another LiteLLM. Not only observability.

> LiteLLM connects models. Helicone shows traffic.  
> **Tollgate keeps agents in line — and proves failover works.**

## Chaos / DR (Prove)

```bash
# Simulate provider outage for 5 minutes (router + invoke skip it)
tollgate chaos start opencode_zen --duration 5m
tollgate chaos status
tollgate chaos stop opencode_zen

# Active test: inject → N routes → report
tollgate chaos test opencode_zen --requests 10 --duration 2m
tollgate resilience
```

Example report shape:

```text
FAILOVER TEST
Requests tested        10
Successful             10
Failed                  0
Automatic failover    100%
Recovery time        ~ms
✓ Application survived opencode_zen outage
```

## Resilience Score

```bash
tollgate resilience
# or GET /v1/resilience
```

```text
AI RESILIENCE  87/100
  reliability        94
  failover           91
  budget_control     82
  provider_diversity 75
  observability      89
```

## Competitive wedge

| Field is crowded with | Tollgate sells |
|----------------------|----------------|
| Multi-provider proxy | **DR proof** + agent protection |
| Post-hoc analytics | **Pre-admission hard stop** |
| K8s / edge gateways | **Simple self-host desk + agents + MCP** |

## Business sketch (later)

| Tier | Scope |
|------|--------|
| Community | 1 host, basic protect/route, chaos test CLI |
| Pro | analytics, chaos reports history, advanced routing |
| Enterprise | RBAC, SSO, multi-region, SLA |

## What we already ship

- Protect: consumer envelopes + agent_guard  
- Route: health-aware ranking + execute failover  
- Prove: `chaos` + `resilience` + dashboard attention  

## What we refuse

- “30 more providers” as roadmap  
- Feature soup without Protect / Route / Prove  
