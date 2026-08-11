# Tollgate — User Guide

**Version:** 1.0.x · **Repo:** https://github.com/landjunge/tollgate  

> **Tollgate is the safety layer between your AI agents and the internet.**  
> Not an API gateway. Not a multi-LLM catalog.

**Killer use case:** *“My AI agent must never go out of control.”*

| Quick links | |
|-------------|--|
| 10-minute cold start | [TEN_MINUTE.md](TEN_MINUTE.md) · `./scripts/ten-minute.sh` |
| Demo | [DEMO.md](DEMO.md) · `tollgate demo` |
| Control Room | http://127.0.0.1:8787/dashboard |
| CLI help | `tollgate help` · `tollgate help protect` |
| German handbook | [HILFE.md](HILFE.md) |

---

## 1. What Tollgate is

```text
Agent / n8n / MCP / OpenAI SDK
            │
            ▼
         TOLLGATE
   Protect · Route · Prove
            │
   ┌────────┼────────┐
   ▼        ▼        ▼
 OpenAI  Anthropic  Zen / DeepSeek / …
```

| Pillar | Job | User question |
|--------|-----|----------------|
| **Protect** | Budgets, tool-loop stops, scopes, freeze, audit | Will this agent run away? |
| **Route** | Health routing, failover, circuits | What if the primary provider dies? |
| **Prove** | Chaos tests, resilience score, certificate | Can I **show** it works? |

**Not:** agent framework · chat memory store · 100-provider SaaS catalog.

---

## 2. Install

**Requires Python ≥ 3.11.**

```bash
git clone https://github.com/landjunge/tollgate.git
cd tollgate
python3 -m venv .venv && .venv/bin/pip install -e .

export TOLLGATE_HOME=$HOME/.tollgate
mkdir -p "$TOLLGATE_HOME/User"
tollgate serve
# → http://127.0.0.1:8787
```

```bash
./scripts/desk-ready.sh      # doctor + server + smoke
./scripts/ten-minute.sh      # Protect → Prove → certificate
```

**Docker:**

```bash
docker compose up -d --build
docker compose exec tollgate tollgate certificate
```

**Protect demo needs no API keys.** Real chat needs keys in `User/Key.txt` (see `Key.txt.example`).

---

## 3. Data layout

| Path under `$TOLLGATE_HOME/User/` | Role |
|----------------------------------|------|
| `Key.txt` | Secrets (never commit) |
| `keys_app.json` | Policy, envelopes, routing, freeze |
| `keys_usage.json` | Daily usage ledger |
| `consumers.json` | Hashed consumer secrets |
| `circuits.json` | Circuit breakers |
| `audit.jsonl` | Append-only audit |
| `chaos.json` | DR / chaos state |

```bash
tollgate doctor
tollgate paths
```

---

## 4. Consumers (agent lanes)

Identity on every request:

```http
X-Consumer-Key: support-agent
# auth mode:
X-Consumer-Key: support-agent:secret
Authorization: Bearer support-agent:secret
```

| Mode | When | Key format |
|------|------|------------|
| **Open** | no consumers / local desk | any label |
| **Auth** | `consumers.json` or `TOLLGATE_REQUIRE_AUTH=1` | `id:secret` |

```bash
tollgate consumer-add n8n
tollgate consumer-add desk --admin
```

---

## 5. Protect

### Envelopes

```bash
tollgate consumer-budget support-agent \
  --max-usd-day 2 \
  --max-usd-request 0.5 \
  --max-requests-minute 50 \
  --max-tool-calls 20

tollgate consumer-budget --list
```

| Field | Meaning |
|-------|---------|
| `max_usd_day` / `_request` / `_hour` | Money caps |
| `max_requests_minute` | RPM |
| `max_tool_calls` | Tool-loop depth this turn |
| `max_tokens_request` | Token estimate cap |

`0` / omit = unlimited on that dimension.

### Scopes

```bash
tollgate consumer-budget support-agent \
  --allow-provider opencode_zen \
  --allow-intent free_llm --allow-op chat
```

### Tool-loop Aha

```bash
curl -s http://127.0.0.1:8787/v1/invoke \
  -H 'Content-Type: application/json' \
  -H 'X-Consumer-Key: support-agent' \
  -d '{"provider":"opencode_zen","op":"chat","tool_calls_est":99,"arguments":{"message":"hi"}}'
```

Response includes `blocked.message` (`🛑 REQUEST BLOCKED`).  
Dashboard: **Test tool-loop block**.

### Freeze

```bash
tollgate freeze --reason "incident"
tollgate unfreeze
# env: TOLLGATE_FROZEN=1
```

---

## 6. Route

```bash
curl -s http://127.0.0.1:8787/v1/route \
  -H 'Content-Type: application/json' \
  -H 'X-Consumer-Key: support-agent' \
  -d '{"intent":"free_llm","tokens_est":1000}'
```

```bash
tollgate circuits list
tollgate circuits reset deepseek
```

---

## 7. Prove

```bash
tollgate chaos test opencode_zen --requests 10
tollgate resilience
tollgate certificate --application "Customer Support Agent"
```

Dashboard → **Prove** → Run test.

---

## 8. Control Room WebUI

http://127.0.0.1:8787/dashboard  

| Screen | Question |
|--------|----------|
| Overview | Safe? Broken? Expensive? What to do? |
| Agents | Protection, budgets, edit, loop test |
| Providers | Health, latency, cost |
| Prove | Chaos + certificate |
| Audit | Who was blocked and why |

Badge: **PROTECTED** · **ATTENTION** · **FROZEN**  
**Setup** wizard: name agent → set limits → save (first lane without CLI).

OpenAPI: http://127.0.0.1:8787/docs  

---

## 9. Connect clients

### OpenAI drop-in

```bash
export OPENAI_BASE_URL=http://127.0.0.1:8787/v1
export OPENAI_API_KEY=support-agent
# models: tollgate/free | tollgate/auto | provider ids
```

Extras: `tool_calls_est`, `tokens_est`.  
See [OPENAI.md](OPENAI.md) · Anthropic: [ANTHROPIC.md](ANTHROPIC.md) · n8n: [N8N.md](N8N.md) · MCP: [MCP.md](MCP.md).

---

## 10. CLI reference

```text
tollgate help [topic]
  topics: start | protect | route | prove | ui | api | ops | troubleshoot
```

| Command | Purpose |
|---------|---------|
| `serve` / `mcp` | HTTP / MCP servers |
| `doctor` | Install/config diagnose |
| `status` / `health` / `paths` | State |
| `certificate` | Reliability scorecard |
| `demo` | Live Protect + Prove |
| `consumer-add` / `consumer-budget` | Lanes + envelopes |
| `chaos` / `resilience` | DR proof |
| `freeze` / `unfreeze` | Kill switch |
| `circuits` | List/reset breakers |
| `audit` / `report` | Trail + day brief |
| `alert` | Webhook catalog/test |
| `snapshot` | Export/import desk |
| `control` / `search` | Control JSON / repo search |
| `high-risk` / `provider-add` / `suggest` | Provider ops |

---

## 11. HTTP API (summary)

| Method | Path | Role |
|--------|------|------|
| GET | `/dashboard` | Control Room |
| GET | `/v1/health` · `/v1/control` · `/v1/status` | Health / pane / glance |
| GET | `/v1/certificate` · `/v1/resilience` | Prove signals |
| GET/POST | `/v1/chaos` · `/v1/chaos/test` | DR |
| GET | `/v1/audit` | Audit query |
| GET/POST | `/v1/config` | Policy (admin when auth) |
| POST | `/v1/route` · `/v1/invoke` | Route / call |
| POST | `/v1/chat/completions` · `/v1/messages` | Drop-ins |
| GET/POST | `/v1/freeze` · `/v1/circuits*` | Ops controls |
| GET | `/metrics` | Prometheus (may require auth) |

Full schemas: `/docs` on a running server.

---

## 12. Ops extras

**Webhooks:** `TOLLGATE_ALERT_WEBHOOK` or `cost_guard.alert_webhook_url` · `tollgate alert test`  

**Snapshot:** `tollgate snapshot export -o desk.tgz` (Key.txt omitted by default)  

**Portable USB:** [PORTABLE.md](PORTABLE.md)

---

## 13. Troubleshooting

| Issue | Check |
|-------|--------|
| Won’t start | `doctor` · port 8787 · Python 3.11+ |
| 401 | Auth mode needs `id:secret` |
| Always blocked | Envelope / freeze / scope |
| Chaos failed | ≥2 providers in chain · keys |
| Stale UI | Hard refresh · `/v1/health` version |
| Metrics 401 | Token / consumer / `TOLLGATE_METRICS_PUBLIC=1` |
| Wrong data dir | `tollgate paths` · `TOLLGATE_HOME` |

---

## 14. Security checklist

- Provider secrets only in vault (`Key.txt`)  
- Use auth mode off localhost  
- Don’t expose `/metrics` or config without auth  
- Ledger holds ops counters only — never chat transcripts  
- Use freeze during incidents  

---

## 15. Doc map

| Doc | Use when |
|-----|----------|
| [TEN_MINUTE.md](TEN_MINUTE.md) | First contact |
| [DEMO.md](DEMO.md) | Pitch / screen share |
| [HILFE.md](HILFE.md) | German full help |
| [PRODUCT.md](PRODUCT.md) | Positioning |
| [COST_LIMITS.md](COST_LIMITS.md) | Envelope fields |
| [OPERATIONS.md](OPERATIONS.md) | Deploy / ops |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Layers |
| [MAP.md](MAP.md) | Code index |

```bash
tollgate search budget
tollgate search --map
```

---

**Pay the toll — or don't call.** · MIT · https://github.com/landjunge/tollgate
