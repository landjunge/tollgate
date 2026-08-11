# Getting started in 5 minutes

**Goal:** Tollgate running, one protected agent lane, dashboard open, optional DR proof.

## 1. Start

```bash
# A) Docker
cd tollgate && docker compose up -d

# B) Local desk
export TOLLGATE_HOME=$HOME/WS-gnom-hub-v1   # or any data dir
./scripts/desk-ready.sh
```

Open:

- Dashboard: http://127.0.0.1:8787/dashboard  
- API docs: http://127.0.0.1:8787/docs  

## 2. Put keys once (not in agents)

```bash
# $TOLLGATE_HOME/User/Key.txt
DEEPSEEK_API_KEY=…
OPENCODE_API_KEY=…     # free path
BRAVE_API_KEY=…        # optional search
```

```bash
tollgate doctor
```

## 3. Protect one agent (2 minutes)

```bash
# Day + loop protection for n8n / coding agent
tollgate consumer-budget n8n \
  --max-usd-day 2 \
  --max-usd-hour 0.5 \
  --max-usd-request 0.25 \
  --max-requests-minute 30 \
  --max-tokens-request 20000 \
  --max-tool-calls 15

tollgate consumer-budget --list
```

Agents send tool depth via invoke:

```json
POST /v1/invoke
{
  "provider": "opencode_zen",
  "op": "chat",
  "tool_calls_est": 12,
  "arguments": { "message": "…" }
}
```

If `tool_calls_est` &gt; `max_tool_calls` → **hard deny** (agent protection).

## 4. Point a client at Tollgate

```bash
export OPENAI_BASE_URL=http://127.0.0.1:8787/v1
export OPENAI_API_KEY=n8n          # open mode label
# model: tollgate/free  or  tollgate/auto
```

```bash
curl -s $OPENAI_BASE_URL/chat/completions \
  -H "Authorization: Bearer n8n" -H "Content-Type: application/json" \
  -d '{"model":"tollgate/free","messages":[{"role":"user","content":"hi"}],"max_tokens":32}'
```

## 5. Prove failover (optional, 1 minute)

```bash
tollgate chaos test opencode_zen --requests 5
tollgate resilience
```

Dashboard → **Disaster recovery** should show *survived*.

## What “done” looks like

| Check | Expect |
|-------|--------|
| `/dashboard` | Resilience score, agents, providers |
| `tollgate doctor` | Key.txt OK; maybe chaos_untested until step 5 |
| Budget list | `n8n` has hard limits |
| Free chat | HTTP 200 via OpenAI base URL |
| Chaos test | `survived: true` if ≥2 providers in free_llm |

## Next

| Doc | Topic |
|-----|--------|
| [PRODUCT.md](PRODUCT.md) | Protect · Route · Prove positioning |
| [N8N.md](N8N.md) | n8n node + workflows |
| [COST_LIMITS.md](COST_LIMITS.md) | envelopes + agent protection fields |
| [OPENAI.md](OPENAI.md) / [ANTHROPIC.md](ANTHROPIC.md) | drop-in SDKs |
| [DESK.md](DESK.md) | daily desk runbook |
