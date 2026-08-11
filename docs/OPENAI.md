# OpenAI-compatible API

Tollgate exposes a **drop-in** surface so existing tools only change `base_url` + API key.

## Setup

```bash
./scripts/run.sh
# or: docker compose up -d

export OPENAI_BASE_URL=http://127.0.0.1:8787/v1
export OPENAI_API_KEY=n8n              # open mode: any label
# with auth:  export OPENAI_API_KEY=n8n:your-secret
```

Python (`openai` SDK):

```python
from openai import OpenAI
client = OpenAI(base_url="http://127.0.0.1:8787/v1", api_key="desk")
r = client.chat.completions.create(
    model="tollgate/free",
    messages=[{"role": "user", "content": "hi"}],
)
print(r.choices[0].message.content)
```

curl:

```bash
curl -s http://127.0.0.1:8787/v1/chat/completions \
  -H "Authorization: Bearer desk" \
  -H "Content-Type: application/json" \
  -d '{"model":"tollgate/auto","messages":[{"role":"user","content":"hi"}]}'
```

## Endpoints

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/v1/models` | OpenAI list shape |
| `POST` | `/v1/chat/completions` | admit + route + meter |

Full OpenAPI: `http://127.0.0.1:8787/docs`

## Model ids

| Model | Behavior |
|-------|----------|
| `tollgate/auto` | intent `llm` → router chain |
| `tollgate/free` | intent `free_llm` (prefer free) |
| `deepseek-v4-flash-free` | free path if Zen available |
| any other id | passed as model hint; router may still pick provider |

Optional body fields (Tollgate-only, SDKs ignore extras):

```json
{
  "intent": "free_llm",
  "provider": "opencode_zen",
  "request_class": "batch",
  "prefer_free": true,
  "tool_calls_est": 3,
  "tokens_est": 1200
}
```

## Agent loop protection (`tool_calls_est`)

`max_tool_calls` on a consumer envelope only works if Tollgate knows the **loop depth**.

| Source | How |
|--------|-----|
| **Body** | `"tool_calls_est": 12` (best — explicit) |
| **Header** | `X-Tollgate-Tool-Calls-Est: 12` |
| **Auto** | Count `role: tool` messages + `assistant.tool_calls` in history |
| **Weak** | `len(tools)` if tools schema present and no history yet |

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8787/v1", api_key="support-agent")

# Explicit (recommended for agent frameworks)
client.chat.completions.create(
    model="tollgate/free",
    messages=[{"role": "user", "content": "hi"}],
    extra_body={"tool_calls_est": 5},  # or pass as top-level if your SDK allows
)

# Header alternative
client.chat.completions.create(
    model="tollgate/free",
    messages=[...],
    extra_headers={"X-Tollgate-Tool-Calls-Est": "5"},
)
```

curl:

```bash
curl -s http://127.0.0.1:8787/v1/chat/completions \
  -H "Authorization: Bearer support-agent" \
  -H "Content-Type: application/json" \
  -H "X-Tollgate-Tool-Calls-Est: 99" \
  -d '{"model":"tollgate/free","messages":[{"role":"user","content":"x"}],"max_tokens":16}'
```

Without any of the above, a plain single-turn chat will **not** hit `max_tool_calls` (est=0).  
Dashboard **Test tool-loop block** always sends an explicit high est.

## Streaming

`stream: true` returns **SSE** (`text/event-stream`).

| Mode | When | Header |
|------|------|--------|
| **upstream** | Provider speaks OpenAI `stream:true` (`deepseek`, `worker`, `opencode_zen`, `openrouter`) | `X-Tollgate-Stream: upstream` |
| **synthetic** | Other providers, or `TOLLGATE_STREAM_SYNTHETIC=1` | `X-Tollgate-Stream: synthetic` |

Upstream mode admits first, then proxies token deltas, then meters usage (ledger + consumer envelope). Synthetic mode still runs a full completion and chunk-splits it for clients that only need `stream: true` compatibility.

## Health-aware routing

`POST /v1/route` (and OpenAI/Anthropic free/auto models that use the router) ranks
**admitted** providers when `routing.health_aware` is true (default):

| `routing.strategy` | Bias |
|--------------------|------|
| `balanced` (default) | reliability + latency + cost + config order |
| `reliability` | health score first |
| `cost_optimized` | lower day spend, still needs health |

Response fields: `strategy`, `ranking[]`, `route.rank_score`, `explain.reasons`.

```bash
curl -s localhost:8787/v1/route -H 'Content-Type: application/json' \
  -d '{"intent":"free_llm","prefer_free":true}' | jq '{provider, strategy, ranking, explain}'
```

Disable: `"routing": { "health_aware": false }` → pure config chain order.

## Failover

When `auto_failover` is true in `keys_app.json` (default) and the client did **not** pin `provider=…`:

1. Router builds primary + up to 3 fallbacks under limits/circuits  
2. `routed_chat` / stream setup **executes** the next candidate if the hop fails with a retriable class:

| Retriable (hop) | Hard stop (no hop) |
|-----------------|--------------------|
| `PROVIDER_DOWN`, `RATE_LIMIT`, `EDGE_BLOCK`, `AUTH_DEAD`, empty completion | `BUDGET_HARD`, `POLICY_DENY` |

Response includes `failover: { tried, winner, hops }`.  
Streaming only fails over **before** the first SSE byte (no mid-stream provider switch).

## Auth

Same as native API:

- `Authorization: Bearer <id>:<secret>`
- or `X-Consumer-Key: <id>:<secret>`
- open mode (no `consumers.json`): any Bearer label works

## Errors

| HTTP | Meaning |
|------|---------|
| 401 | consumer / key |
| 402 | budget / policy deny |
| 429 | rate limit |
| 502/503 | upstream / circuit |

Body follows OpenAI `{"error":{"message","type","code"}}` plus Tollgate still returns native `error_class` on internal paths.

## What this is not

- Not a full OpenAI product (vision tools, assistants, files, …)
- Does **not** store chat history (no gateway memory)

## Related surfaces

| Path | Role |
|------|------|
| `/metrics` | Prometheus (ledger, circuits, cache) |
| Webhook | `cost_guard.alert_webhook_url` / `TOLLGATE_ALERT_WEBHOOK` |
| Docker | `docker compose up -d` |
