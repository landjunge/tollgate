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
  "prefer_free": true
}
```

## Streaming

`stream: true` returns **SSE** (`text/event-stream`).

| Mode | When | Header |
|------|------|--------|
| **upstream** | Provider speaks OpenAI `stream:true` (`deepseek`, `worker`, `opencode_zen`, `openrouter`) | `X-Tollgate-Stream: upstream` |
| **synthetic** | Other providers, or `TOLLGATE_STREAM_SYNTHETIC=1` | `X-Tollgate-Stream: synthetic` |

Upstream mode admits first, then proxies token deltas, then meters usage (ledger + consumer envelope). Synthetic mode still runs a full completion and chunk-splits it for clients that only need `stream: true` compatibility.

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
