# Tollgate

**Pay the toll — or don't call.**

Local, multi-consumer **API admission gate** for AI agents.  
One place holds secrets, budgets, and routing — so Gnom, n8n, Cursor/MCP, and anything else never each invent their own spend logic.

> As soon as you run **more than one** AI tool against paid keys, you need an instance that never puts secrets in agent memory and never spends more than you allowed — no matter which tool calls.

## Who it's for

| Audience | Why |
|----------|-----|
| Solo builders with several local agents | Shared keys without bill-shock loops |
| n8n power users | No native LLM budget gate in n8n |
| MCP users (Cursor / Claude Desktop) | One admission plane, not N auth setups |
| Agencies (with care) | Need real consumer secrets first — we have hashed keys |

**Not competing for:** full LiteLLM/Portkey cloud parity. Differentiator = **local, MCP-native, pre-admission, USB-portable**.

## vs LiteLLM / Portkey / OpenRouter

| | **Tollgate** | LiteLLM Proxy | Portkey | OpenRouter alone |
|--|--------------|---------------|---------|------------------|
| Runs fully local | ✅ | ✅ (self-host) | Cloud-first | Cloud API |
| Pre-admission $ hard deny | ✅ core | optional | policies | no local budget |
| Secrets never in agent | ✅ vault | yes | yes | keys in each client |
| Distill-as-data (provider facts) | ✅ JSON SSoT | code/config mix | dashboard | catalog |
| MCP stdio first-class | ✅ | via adapters | — | — |
| USB / portable desk | ✅ | DIY | — | — |
| Multi-tenant SaaS | ❌ not the goal | partial | ✅ | N/A |
| Huge provider catalog | thin + scaffold | large | large | large |

Steal ideas, not the stack — see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Quick start

```bash
cd tollgate
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
./scripts/portable-setup.sh   # optional USB sibling WS-tollgate
# put keys in $TOLLGATE_HOME/User/Key.txt  (see Key.txt.example)
./scripts/run.sh
# → http://127.0.0.1:8787/docs   ← OpenAPI SSoT for request shapes
```

### Consumer auth (share with n8n / second host)

```bash
tollgate consumer-add n8n
tollgate consumer-add desk --admin
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
docker compose up -d               # optional
curl -s localhost:8787/metrics | head   # Prometheus
```

→ [docs/OPENAI.md](docs/OPENAI.md)

Review-Liste: **OpenAI ✅ · Docker ✅ · Webhooks ✅ · Prometheus ✅** · Anthropic/n8n-Node/LiteLLM-Import → on demand.

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
