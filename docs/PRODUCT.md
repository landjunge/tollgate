# Tollgate product direction

**Positioning (locked direction 2026-08-11):**

> **Tollgate is the control plane between your AI applications and model providers.**

Not “another AI gateway.” Existing gateways **route** traffic. Tollgate **governs AI traffic**.

## Three promises

| Pillar | Promise |
|--------|---------|
| **Reliability** | Failover, circuits, provider health — agents keep working when a provider degrades |
| **Cost** | Hard budgets, envelopes per consumer/agent, burn projection — no silent $500 nights |
| **Control** | Admission, audit, “why this model?”, policy — spend is explainable |

Everything shipping maps under those three.

## What we are not

- Competing with Kong/Envoy/LiteLLM on “more protocol adapters”
- Cloud multi-tenant SaaS first
- Semantic ranking before admission is boring and correct

## Audiences (priority order)

1. **AI-agent builders / startups** — multi-provider agents, bill-shock, automatic cheaper/healthier paths  
2. **Companies with many AI tools** — one control plane for 20 devs / N tools  
3. **n8n / automation** — workflows + loops + retries without unbounded spend  
4. **Self-hosted AI** — Ollama/vLLM + paid APIs behind one admit surface  

## Priority roadmap

| P | Feature | Status |
|---|---------|--------|
| P0 | Stability + config back-compat | continuous (see PR #7 legacy circuits) |
| P0 | **Provider health intelligence** | **v0.2** — `/v1/control` |
| P0 | **Cost per consumer/agent + projection** | **v0.2** — control plane + budget |
| P1 | Smarter health-aware routing | partial (failover + scores feed) |
| P1 | **Why this model?** explainability | **v0.2** — `explain` on route |
| P1 | Budget alerts / webhooks | soft_warn exists; expand |
| P2 | Team/org management | later |
| P2 | Richer audit product | `audit.jsonl` exists |
| P2 | Web dashboard (feelable) | **v0.2 mini** — `/dashboard` |
| P3 | Enterprise SSO/RBAC | later |

## Feelable product

A control plane must be **seen**, not only curled:

```text
$73 protected today · 4 provider failures absorbed · 12 agent lanes under envelope
```

`/dashboard` and `GET /v1/control` are the first surface for that headline.
