# Cost limits (especially Google)

Google/Gemini/Vertex are **easy to overspend**: multimodal, grounding, long context, GCP billing attached quietly.

## Defaults (safe) — code SSoT

From `DEFAULT_CONFIG` in `src/tollgate/app_config.py` (written into `keys_app.json` on first load):

| Setting | Value |
|---------|--------|
| `providers.google.enabled` | **false** |
| `providers.google.max_usd_day` | **1.0** |
| `providers.google.max_calls_day` | **20** |
| `providers.google.max_tokens_day` | **50_000** |
| `providers.google.max_tokens_call` | **8_000** |
| `cost_guard.max_usd_day_global` | **5.0** |
| `cost_guard.require_explicit_enable_for_high_risk` | **true** |
| `cost_guard.high_risk_providers` | `google`, `gemini`, `vertex` (extend freely) |
| `cost_guard.soft_warn_ratio` | **0.8** (soft pressure + optional webhook) |
| `cost_guard.alert_webhook_url` | empty (or `TOLLGATE_ALERT_WEBHOOK`) |
| Routing | high-risk ids **not** in `free_llm` by default |

Router uses **`is_provider_enabled()`**, never “key present ⇒ enabled”.  
High-risk is **generic**: config list ∪ distill `high_risk` ∪ `providers.<id>.high_risk`.

```bash
tollgate high-risk add azure_openai
tollgate provider-add my_corp_llm --high-risk --auth bearer --env-key MY_CORP_KEY
```

## Config file locations

| Env / path | Role |
|------------|------|
| `$TOLLGATE_HOME/User/keys_app.json` | Preferred |
| `$GNOM_WS/User/keys_app.json` | Gnom-compat while migrating |
| `~/.tollgate/User/keys_app.json` | Default home |
| `$TOLLGATE_CONFIG` / `$GNOM_KEYS_CONFIG` | Absolute override path |

Secrets stay in `User/Key.txt` — **not** in `keys_app.json`.

## Edit limits

### A) Edit the JSON file

```json
{
  "cost_guard": { "max_usd_day_global": 3.0 },
  "providers": {
    "google": {
      "enabled": false,
      "max_usd_day": 0.5,
      "max_calls_day": 10
    }
  }
}
```

### B) HTTP (Tollgate **:8787** only)

Server must be running: `tollgate serve` → bind **127.0.0.1** only unless you add real auth.

`POST /v1/config` runs the **same schema/semantic validation** as process start
(`validate_config_dict`) and returns **HTTP 400** if the merged config would be invalid.
Invalid patches are **not** written.

```bash
# Read (limits + routing — no API keys in this file)
curl -s http://127.0.0.1:8787/v1/config | jq .

# Cap global spend (deep-merge patch)
curl -s -X POST http://127.0.0.1:8787/v1/config \
  -H 'Content-Type: application/json' \
  -H 'X-Consumer-Key: desk' \
  -d '{"cost_guard":{"max_usd_day_global":3.0}}'

# Enable Google only with hard caps (only if you really must)
curl -s -X POST http://127.0.0.1:8787/v1/config \
  -H 'Content-Type: application/json' \
  -H 'X-Consumer-Key: desk' \
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

### C) MCP

`keys_config_get` / `keys_config_patch` (same deep-merge semantics).

## Security note

| Endpoint | Risk today |
|----------|------------|
| `GET /v1/providers` | Key values **masked** in inventory cards |
| `GET`/`POST` `/v1/config` | Policy only (`keys_app.json`), not `Key.txt`. **Admin scope** when consumers.json is active (`consumer-add desk --admin`). |
| Consumer envelopes | Lane caps in `consumer_envelopes`; open mode uses header **label** only |

Hashed consumer keys + admin scope: ship. For multi-host: set `TOLLGATE_REQUIRE_AUTH=1` / populate consumers.json; bind loopback unless you trust the network.

## Per-consumer envelopes (n8n vs Gnom)

Provider caps and `max_usd_day_global` still apply. Additionally, each **consumer lane**
(header `X-Consumer-Key` / open-mode label) can have its own day envelope:

```json
{
  "consumer_envelopes": {
    "_default": { "max_calls_day": 0, "max_tokens_day": 0, "max_usd_day": 0 },
    "n8n":  { "max_calls_day": 200, "max_tokens_day": 500000, "max_usd_day": 0.5 },
    "gnom": { "max_calls_day": 5000, "max_usd_day": 3.0 }
  }
}
```

`0` / omit = **no consumer-level cap** on that dimension. Ledger tracks
`keys_usage.json → consumers.<id>`.

**Default policy (desk-friendly, not multi-tenant-safe):** `_default` is all zeros —
an unknown consumer is limited only by **provider** + **global** cost_guard until you
set an envelope. That is intentional for local testing ("pay the toll" still applies
at global/provider hard stops). For production agents:

```bash
# tighten unknown lanes
tollgate consumer-budget _default --max-usd-day 1 --max-requests-minute 60
# and explicit per-agent caps
tollgate consumer-budget coding-agent --max-usd-day 20 --max-tool-calls 15
```

### Agent protection (loop / runaway stops)

Same envelope block supports short-window hard stops:

| Field | Stops |
|-------|--------|
| `max_usd_request` | Single call est. $ too high |
| `max_usd_hour` | Hourly spend window |
| `max_requests_minute` | Request flood / tight loops |
| `max_tokens_request` | Oversized prompts |
| `max_tool_calls` | Tool-loop depth (client sends `tool_calls_est`) |

```bash
tollgate consumer-budget n8n --max-usd-day 0.5 --max-calls-day 200
tollgate consumer-budget coding-agent \
  --max-usd-day 20 --max-usd-hour 5 --max-usd-request 0.5 \
  --max-requests-minute 30 --max-tokens-request 20000 --max-tool-calls 15
tollgate consumer-budget --list
curl -s localhost:8787/v1/budget -H 'X-Consumer-Key: n8n' | jq .consumer_limits
```

On breach: admit **fails closed**, audit row + optional webhook (`agent_protection`).

Works in **open mode** (label only) and **auth mode** (id:secret). Admission denies with
`consumer <id> max_*_day reached` before the provider call.

## Prefer instead of Google

- **OpenCode Zen free** (`deepseek-v4-flash-free`, …)
- **DeepSeek** (cheap paid)
- **NVIDIA NIM** catalog free tier
- **Brave** for search (not Google Search API)

## Distill

Full warnings: [`src/tollgate/distill/google.json`](../src/tollgate/distill/google.json)
