# Anthropic-compatible API

Tollgate exposes a **Messages API drop-in** so Anthropic SDKs / tools only change
base URL + API key. Spend still goes through admit, budgets, circuits, and consumer envelopes.

**Does not require an Anthropic provider key** — traffic is routed to your Tollgate
LLM providers (Zen free, DeepSeek, OpenRouter, …).

## Setup

```bash
./scripts/run.sh

export ANTHROPIC_BASE_URL=http://127.0.0.1:8787
export ANTHROPIC_API_KEY=desk              # open mode: any label
# with auth:  export ANTHROPIC_API_KEY=n8n:your-secret
```

Python (`anthropic` SDK):

```python
import anthropic

client = anthropic.Anthropic(
    base_url="http://127.0.0.1:8787",
    api_key="desk",
)
msg = client.messages.create(
    model="tollgate/free",
    max_tokens=64,
    messages=[{"role": "user", "content": "hi"}],
)
print(msg.content[0].text)
```

curl:

```bash
curl -s http://127.0.0.1:8787/v1/messages \
  -H "x-api-key: desk" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "tollgate/free",
    "max_tokens": 64,
    "system": "Be brief.",
    "messages": [{"role": "user", "content": "hi"}]
  }'
```

## Endpoint

| Method | Path | Notes |
|--------|------|--------|
| `POST` | `/v1/messages` | admit + route + meter |

`anthropic-version` header is accepted and ignored (SDK compat).

Auth (any one):

- `x-api-key: <id>:<secret>` (Anthropic style)
- `Authorization: Bearer <id>:<secret>`
- `X-Consumer-Key: <id>:<secret>`

## Model ids

| Model | Behavior |
|-------|----------|
| `tollgate/auto` | intent `llm` |
| `tollgate/free` | intent `free_llm` |
| `claude-*` | treated as auto (router picks real provider) |
| other | model hint for router |

Optional Tollgate body fields: `intent`, `provider`, `request_class`, `prefer_free`.

## Streaming

`stream: true` → Anthropic SSE events:

`message_start` → `content_block_start` → `content_block_delta`* → `content_block_stop` → `message_delta` → `message_stop`

Upstream token stream when the backend provider supports OpenAI streaming; otherwise synthetic text chunks. Headers: `X-Tollgate-Stream`, `X-Tollgate-Compat: anthropic`.

## Response shape

```json
{
  "id": "msg_…",
  "type": "message",
  "role": "assistant",
  "content": [{"type": "text", "text": "…"}],
  "model": "…",
  "stop_reason": "end_turn",
  "usage": {"input_tokens": 10, "output_tokens": 5}
}
```

Errors: `{"type":"error","error":{"type":"…","message":"…"}}` (402 budget, 401 auth, …).

## What this is not

- Not a real Anthropic proxy (no Claude API key required or used by default)
- No tools / vision / prompt caching product surface yet
- Does **not** store chat history
