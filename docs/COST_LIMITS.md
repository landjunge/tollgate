# Cost limits (especially Google)

Google/Gemini/Vertex are **easy to overspend**: many products, multimodal, grounding, long context, GCP billing attached quietly.

## Defaults (safe)

| Setting | Value |
|---------|--------|
| `providers.google.enabled` | **false** |
| `providers.google.max_usd_day` | **1.0** |
| `providers.google.max_calls_day` | **20** |
| `providers.google.max_tokens_day` | **50_000** |
| `cost_guard.max_usd_day_global` | **5.0** |
| `cost_guard.require_explicit_enable_for_high_risk` | **true** |
| Routing | Google **not** in free_llm / default llm chain |

## Edit limits

File: `WS-gnom-hub-v1/User/keys_app.json`

Or API:

```bash
# Cap global spend
curl -s -X POST http://127.0.0.1:8080/api/keys/config \
  -H 'Content-Type: application/json' \
  -d '{"cost_guard":{"max_usd_day_global":3.0}}'

# Enable Google only with hard caps (only if you really must)
curl -s -X POST http://127.0.0.1:8080/api/keys/config \
  -H 'Content-Type: application/json' \
  -d '{
    "providers": {
      "google": {
        "enabled": true,
        "max_usd_day": 0.5,
        "max_calls_day": 10,
        "max_tokens_day": 20000,
        "max_tokens_call": 4000
      }
    }
  }'
```

## Prefer instead of Google

- **OpenCode Zen free** (`deepseek-v4-flash-free`, …)
- **DeepSeek** (cheap paid)
- **NVIDIA NIM** catalog free tier
- **Brave** for search (not Google Search API)

## Distill

Full warnings: `src/gnom_hub/keys/distill/google.json`
