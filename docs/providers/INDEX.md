# Provider distillates (human index)

Machine facts: `src/gnom_hub/keys/distill/*.json`  
This folder is the **readable** companion. Prefer JSON for tooling.

## Function map (Hub / MCP)

| Provider | Primary ops (from distill) |
|----------|----------------------------|
| **deepseek** | status, models, research |
| **worker** | status, models, research |
| **brave** | status, search, quota, research |
| **elevenlabs** | status, subscription, budget, ensure_budget, research |
| **openrouter** | status, credits, models, research |
| **nvidia** | status, models, research |
| **minimax** | status, probe, research |
| **opencode_zen** | status, models, chat, research |
| **telegram** | status, research |
| **google** | status, research — **DISABLED by default, high cost risk** |

Meta (not a provider): dashboard, diagnose, route, preflight, usage, config, auto_update.

**Money guard:** see [COST_LIMITS.md](../COST_LIMITS.md) — Google stays off until you enable it with `max_usd_day`.

## Auth cheat sheet

| Provider | Header / scheme |
|----------|-----------------|
| deepseek / worker | `Authorization: Bearer` |
| openrouter / nvidia / minimax / zen | `Authorization: Bearer` |
| brave | `X-Subscription-Token` |
| elevenlabs | `xi-api-key` |
| telegram | path `/bot<token>/…` |

## Cost cheat sheet

| Provider | Probe cost | Spend unit |
|----------|------------|------------|
| deepseek | free | tokens |
| brave | **1 search** | requests |
| elevenlabs | free (sub read) | characters/credits |
| openrouter | free (/key) | credits |
| nvidia | free | catalog quotas |
| opencode_zen | free models $0 | balance for paid |
| minimax | free probe | tokens/audio |
| telegram | free | n/a |

## Do not thrash code

When docs change: **edit distill JSON**.  
Handlers stay thin: call endpoint described by distill `ops[].maps_to`.
