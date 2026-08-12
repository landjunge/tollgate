# How it works — Protect · Route · Prove

Tollgate is the **safety layer between your AI agents and the internet**.  
Not a model catalog. Not multi-tenant SaaS.

```text
Your app / n8n / agent
        │
        ▼
   TOLLGATE   ← admit · budget · loops · freeze · scopes
        │
        ▼
   Providers (OpenAI, DeepSeek, Zen, …) + tools
```

---

## Protect

**Stop cost explosions and runaway tool loops before the call leaves the desk.**

- Per-agent (consumer) budgets and rate limits  
- `max_tool_calls` hard deny (send `tool_calls_est` or let history count tool turns)  
- Global **freeze** kill switch  
- Scopes: allow/block providers, intents, ops  
- Defaults: `_default` envelope is **on** out of the box  

*Connect the agent → protection applies. Tighten later.*

---

## Route

**Survive provider failures.**

- Health-aware routing and failover chains  
- Circuit breakers (disk-backed, multi-worker aware)  
- Prefer free / healthy when configured  

---

## Prove

**Evidence, not vibes.**

- Chaos / DR test (`tollgate chaos test` or Dashboard → Prove)  
- AI Reliability certificate scorecard (`tollgate certificate`)  
- Audit: who was blocked and why  
- Operator report and Control Room  

---

## Surfaces

| Surface | Use |
|---------|-----|
| `POST /v1/chat/completions` | OpenAI SDK drop-in |
| `POST /v1/messages` | Anthropic-style drop-in |
| MCP / n8n | Ops + automation |
| `/dashboard` | Control Room (ops pane) |

---

## Core vs Organization

| Core (today) | Organization (later) |
|--------------|----------------------|
| Full product for **one operator** | Multi-team, SSO/RBAC, fleet |
| Not a feature-paywall | Operating model above Core |

See [PRODUCT_TIERS.md](PRODUCT_TIERS.md).

---

## See also

- [QUICKSTART.md](QUICKSTART.md) — install in minutes  
- [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) — before production  
