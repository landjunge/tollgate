# n8n + Tollgate

n8n holds **no** DeepSeek/Brave/Google secrets — only a consumer id + secret when auth is enabled.

**Product:** https://github.com/landjunge/tollgate

## Run Tollgate

```bash
# desk or USB
./scripts/run.sh
# → http://127.0.0.1:8787/docs
```

Portable stick: see [PORTABLE.md](PORTABLE.md).

### Optional auth (recommended if n8n is not only-localhost)

```bash
tollgate consumer-add n8n
# → secret printed once
# Header becomes: X-Consumer-Key: n8n:<secret>
```

Without consumers.json, open mode accepts any `X-Consumer-Key` label (desk).

### Cap n8n spend independently of Gnom

```bash
tollgate consumer-budget n8n --max-usd-day 0.5 --max-calls-day 200
# remaining / used:
curl -s http://127.0.0.1:8787/v1/budget -H 'X-Consumer-Key: n8n'
```

Envelopes live in `keys_app.json` → `consumer_envelopes`. See [COST_LIMITS.md](COST_LIMITS.md).

## OpenAI-Node (einfachste Variante)

Viele n8n AI-Nodes sprechen OpenAI-Format:

- Base URL: `http://127.0.0.1:8787/v1`
- API Key: `n8n` (open) oder `n8n:<secret>`
- Model: `tollgate/free` oder `tollgate/auto`

Siehe [OPENAI.md](OPENAI.md).

## Example HTTP nodes (native)

### 1) Route free LLM

- Method: `POST`
- URL: `http://127.0.0.1:8787/v1/route`
- Header: `X-Consumer-Key: n8n` (open) or `n8n:<secret>` (auth)
- Body:

```json
{
  "intent": "free_llm",
  "tokens_est": 2000,
  "prefer_free": true
}
```

Use `route.provider` + `route.model` in the next node.

### 2) Invoke (admit + call)

```json
{
  "provider": "opencode_zen",
  "op": "chat",
  "arguments": {
    "message": "={{ $json.prompt }}",
    "model": "deepseek-v4-flash-free",
    "max_tokens": 256
  },
  "agent_id": "n8n-workflow-42",
  "job_id": "={{ $execution.id }}",
  "request_class": "batch"
}
```

POST `http://127.0.0.1:8787/v1/invoke`

### 3) Budget check

`GET http://127.0.0.1:8787/v1/budget?provider=opencode_zen`

### 4) Web search (via gateway limits)

```json
{
  "provider": "brave",
  "op": "search",
  "arguments": { "query": "…", "count": 5 },
  "request_class": "batch",
  "agent_id": "n8n-search"
}
```

## Later

- Credential type `keysGatewayApi` (consumer secret)
- Official community node packing route/invoke/budget
- Per-consumer `max_usd_day` in `keys_app.json`
