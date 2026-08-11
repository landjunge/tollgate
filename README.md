# Tollgate

**Pay the toll — or don't call.**

> **AI Reliability & Control Plane** — Protect · Route · **Prove**.

Protects apps from **provider outages**, **runaway costs**, and **agent loops** — and **proves** failover works (chaos tests).  
Not another LLM gateway.

```bash
tollgate chaos test opencode_zen --requests 10   # DR proof
tollgate resilience                              # AI Resilience Score
```

> As soon as you run **more than one** AI tool against paid keys, you need an instance that never puts secrets in agent memory and never spends more than you allowed — no matter which tool calls.

**Feel it:** `http://127.0.0.1:8787/dashboard` · JSON: `GET /v1/control`  
**5 minutes:** [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)

```bash
./scripts/desk-ready.sh
tollgate consumer-budget n8n --max-usd-day 2 --max-tool-calls 15
tollgate chaos test opencode_zen --requests 5
tollgate resilience
```

## Who it's for

| Audience | Why |
|----------|-----|
| Solo builders with several local agents | Shared keys without bill-shock loops |
| n8n power users | No native LLM budget gate in n8n |
| MCP users (Cursor / Claude Desktop) | One admission plane, not N auth setups |
| Agencies (with care) | Need real consumer secrets first — we have hashed keys |

**Not competing for:** LiteLLM catalog width or Portkey cloud suite.  
**Wedge:** *LiteLLM connects models. Helicone shows traffic. **Tollgate keeps agents in line.***  
Self-hosted · MCP-native · pre-admission hard stops · USB-portable. Details: [docs/PRODUCT.md](docs/PRODUCT.md).

## vs LiteLLM / Portkey / Helicone

| | **Tollgate** | LiteLLM | Portkey | Helicone |
|--|--------------|---------|---------|----------|
| Core job | **Agent protection + control** | Multi-provider proxy | Managed prod stack | Observability + gateway |
| Runs fully local | ✅ first-class | ✅ | cloud-first | cloud / hybrid |
| Pre-admission $ / loop hard deny | ✅ core | optional | policies | mostly post-hoc |

| Secrets never in agent | ✅ vault | yes | yes | keys in each client |
| Distill-as-data (provider facts) | ✅ JSON SSoT | code/config mix | dashboard | catalog |
| MCP stdio first-class | ✅ | via adapters | — | — |
| USB / portable desk | ✅ | DIY | — | — |
| Multi-tenant SaaS | ❌ not the goal | partial | ✅ | N/A |
| Huge provider catalog | thin + scaffold | large | large | large |

Steal ideas, not the stack — see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Quick start

```bash
# A) Docker (lowest friction)
docker compose up -d
# data volume holds User/Key.txt — copy Key.txt.example in, then:
# docker compose exec tollgate tollgate doctor

# B) Local
python3 -m venv .venv && .venv/bin/pip install -e .
./scripts/portable-setup.sh          # optional USB
# edit $TOLLGATE_HOME/User/Key.txt
tollgate doctor                      # self-diagnose first
./scripts/run.sh                     # → http://127.0.0.1:8787/docs
```

```bash
tollgate suggest                     # ledger-based proposals (never auto-applies)
```

### Consumer auth (share with n8n / second host)

```bash
tollgate consumer-add n8n
tollgate consumer-add desk --admin
# optional day envelopes (n8n vs gnom lanes)
tollgate consumer-budget n8n --max-usd-day 0.5 --max-calls-day 200
tollgate consumer-budget --list
# Header: X-Consumer-Key: n8n:<secret>
# Open mode if no consumers.json (local desk only)
```

### High-risk providers (not just Google)

```bash
tollgate high-risk list
tollgate high-risk add azure_openai   # disabled until enabled=true + $ caps
tollgate provider-add azure_openai --base-url https://… --high-risk --env-key AZURE_OPENAI_API_KEY
```

Config: `cost_guard.high_risk_providers` + distill `high_risk: true`.

### Soft budget warnings

At 80% of day budget (configurable), admit returns soft pressure and can POST to a webhook:

```json
"cost_guard": {
  "soft_warn_ratio": 0.8,
  "alert_webhook_url": "https://your-n8n-or-telegram-hook"
}
```

Or env: `TOLLGATE_ALERT_WEBHOOK=…`

## OpenAI drop-in (größter Kompatibilitäts-Hebel)

```bash
export OPENAI_BASE_URL=http://127.0.0.1:8787/v1
export OPENAI_API_KEY=n8n:secret   # open mode: any label works
# POST /v1/chat/completions  ·  GET /v1/models  ·  stream: true → SSE
# POST /v1/messages          ·  Anthropic Messages drop-in (x-api-key)
# n8n: community node n8n-nodes-tollgate/ · configs/n8n-*.workflow.json · ./scripts/n8n-smoke.sh
docker compose up -d               # optional
curl -s localhost:8787/metrics | head   # Prometheus
```

→ [docs/OPENAI.md](docs/OPENAI.md)

Review-Liste: **OpenAI ✅ · Anthropic ✅ · Stream ✅ · Failover ✅ · n8n node ✅ · Docker ✅ · Webhooks ✅ · Prometheus ✅ · Consumer envelopes ✅**.

## HTTP native (kurz)

**Signaturen:** laufender Server → `/docs`.

| Path | Zweck |
|------|--------|
| `GET /v1/health` | portable + auth mode |
| `POST /v1/route` | intent → provider |
| `POST /v1/invoke` | admit + call + meter |
| `GET` / `POST /v1/config` | policy (admin when auth on) |

Contract tests: `tests/test_contract_v1.py`, `tests/test_openai_compat.py`.

## MCP

```bash
python -m tollgate
```

See `configs/mcp-tollgate.example.json` and [docs/MCP.md](docs/MCP.md).

## Config layout

| Path | Role |
|------|------|
| `$TOLLGATE_HOME/User/Key.txt` | Secrets |
| `$TOLLGATE_HOME/User/keys_app.json` | Limits, high_risk list, routing |
| `$TOLLGATE_HOME/User/keys_usage.json` | Ledger |
| `$TOLLGATE_HOME/User/consumers.json` | Hashed consumer secrets |

Portable/USB: [docs/PORTABLE.md](docs/PORTABLE.md).

## Docs & quality gates

- [OPENAI.md](docs/OPENAI.md) · [VISION.md](docs/VISION.md) · [ARCHITECTURE.md](docs/ARCHITECTURE.md) · [N8N.md](docs/N8N.md)

```bash
./scripts/check_docs_drift.sh
./scripts/check_migration.sh
pytest -q
```

## Gnom

Gnom is **one client**. Install Tollgate; do not re-embed the keys tree.

```python
from tollgate import routed_chat, gateway_search, get_keys_service
```
