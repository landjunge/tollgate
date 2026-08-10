# Keys mini-app

Almost a standalone app inside Gnom-Hub: **secrets, limits, token ledger, routing, auto-update**.

Not “is the string set?” — researched APIs, grades A–F, call/token/char budgets, smart failover, configurable everything.

## Provider docs (source of truth — stop code thrash)

**Functions, auth, endpoints, limits** live in distillates, not scattered Python:

| Layer | Path |
|-------|------|
| Machine | `src/gnom_hub/keys/distill/<provider>.json` |
| Human index | `docs/keys/README.md` · `docs/keys/providers/INDEX.md` |
| Loader | `keys/distill/loader.py` → `research_for()` / MCP `keys_research` |

**Update rule:** change JSON when docs change; only touch handlers if a *new op type* is needed.
## Architecture

```
gnom_hub/keys/
  app_config.py       # keys_app.json — enable, limits, routing, auto_update
  usage_ledger.py     # keys_usage.json — tokens/calls/chars per day
  limits.py           # enforce max_calls_day / max_tokens_day / min_interval
  router.py           # intent → provider chain + failover
  auto_update.py      # background refresh (models/status)
  research_notes.py   # auth, limits, errors, gotchas
  catalog.py schema.py policy.py service.py httputil.py
  deepseek.py brave.py elevenlabs.py openrouter.py nvidia.py …
```

## Config file (settable)

Path: `WS-gnom-hub-v1/User/keys_app.json` (auto-created)

```json
{
  "prefer_free": true,
  "auto_failover": true,
  "record_usage": true,
  "auto_update": { "enabled": true, "interval_s": 300, "live_probes": false },
  "routing": {
    "intents": {
      "llm": ["opencode_zen", "deepseek", "nvidia", "openrouter"],
      "free_llm": ["opencode_zen", "nvidia", "openrouter"],
      "search": ["brave"],
      "tts": ["elevenlabs"]
    },
    "models": { "opencode_zen": "deepseek-v4-flash-free", "deepseek": "deepseek-v4-flash" }
  },
  "providers": {
    "opencode_zen": { "enabled": true, "priority": 100, "max_calls_day": 5000, "max_tokens_day": 5000000 },
    "brave": { "enabled": true, "max_calls_day": 500, "min_interval_ms": 1100 },
    "elevenlabs": { "enabled": true, "max_chars_day": 5000, "min_remaining": 5000 },
    "deepseek": { "enabled": true, "max_tokens_day": 2000000, "max_tokens_call": 32000 }
  }
}
```

Patch via API: `POST /api/keys/config` with a partial JSON merge.

## Grades

| Grade | Meaning |
|-------|---------|
| **A** | Live-verified, healthy headroom |
| **B** | Ready (presence or light limits) |
| **C** | Constrained (low credits / quota) |
| **D** | Degraded / unverified / blocked spend |
| **F** | Missing or dead |

## Python API

```python
from gnom_hub.keys import get_keys_service
ks = get_keys_service()

ks.dashboard()                          # pane of glass
ks.diagnose(live=True)                  # issues + actions
ks.inventory(live=False)                # graded cards
ks.preflight("tts", cost=200)           # may I spend?
ks.preflight("search")
ks.preflight("free_llm")
ks.recommend(prefer_free=True)          # Zen free → …

ks.call("elevenlabs", "budget", cost=100)
ks.call("brave", "search", query="xAI", count=3)
ks.call("opencode_zen", "chat", message="hi", model="deepseek-v4-flash-free")
ks.call("openrouter", "credits")
ks.research("brave")
```

## HTTP API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/keys` | Dashboard + usage + smart_route |
| GET | `/api/keys/app` | Mini-app status paths |
| GET | `/api/keys/usage` | Today’s token/call ledger |
| GET | `/api/keys/config` | Full keys_app.json |
| POST | `/api/keys/config` | Deep-merge config patch |
| GET | `/api/keys/route?intent=llm&tokens_est=2000` | Provider pick + fallbacks |
| GET | `/api/keys/{id}/limits` | Remaining call/token budget |
| POST | `/api/keys/auto-update/{start\|stop\|once}` | Background updater |
| GET | `/api/keys/inventory` | Graded inventory |
| GET | `/api/keys/diagnose` | Issues + next actions |
| GET | `/api/keys/preflight?intent=tts&cost=100` | Spend gate |
| GET | `/api/keys/{provider}` | One provider status |
| POST | `/api/keys/{provider}/{op}` | Op + **auto token count** |

## Token counting

Every cost op (`chat`, `search`, `models`, …) appends to `User/keys_usage.json`:

- `calls`, `tokens_in`, `tokens_out`, `tokens`, `chars`, `by_op`
- Daily rollover at local midnight
- Response includes `usage_today` + `limits_remaining`

Snapshot embeds cheap summary: `snapshot()["keys"]`.

## Agent tools

| Tool | Use |
|------|-----|
| `keys_dashboard` | Full dashboard |
| `keys_diagnose` | Fix list |
| `keys_status` | Inventory / one provider |
| `keys_call` | Provider ops + meta (`provider=keys op=preflight`) |
| `elevenlabs_budget` | EL floor alias |
| `web_search` | Brave search |

## Provider matrix (high level)

| Provider | Auth | Probe cost | Specials |
|----------|------|------------|----------|
| deepseek | Bearer | free | models |
| brave | X-Subscription-Token | 1 search (60s cache) | search, quota |
| elevenlabs | xi-api-key | free sub | budget floor 5000 |
| openrouter | Bearer chain | free /key | credits, models |
| nvidia | Bearer nvapi- | free | models |
| opencode_zen | Bearer (+ browser UA) | free chat | models, chat |
| minimax | Bearer regions | free | probe (2049=dead) |
| telegram | optional | getMe | — |

## Add a provider

1. `research_notes.py` entry with `researched_at`
2. `catalog.py` KeyFamily + HUB_OWNED
3. `keys/<name>.py` with `status()` + ops
4. Register in `service.py` `_STATUS` / `_OPS`
5. Caps in `schema.PROVIDER_CAPS`
6. Unit tests (mock, no network)

## MCP

Full guide: [KEYS_MCP.md](KEYS_MCP.md)

```bash
# stdio server (Cursor / Claude)
PYTHONPATH=src GNOM_WS=$HOME/WS-gnom-hub-v1 .venv/bin/python -m gnom_hub.keys.mcp

# HTTP
curl -s http://127.0.0.1:8080/api/mcp/keys/tools | jq '.tools[].name'
```

Example client config: `configs/mcp-gnom-keys.example.json`

## Live smoke

```bash
PYTHONPATH=src .venv/bin/python scripts/keys_live_smoke.py
```

## Rules

1. Research before code  
2. Presence ≠ ready (except documented presence-only)  
3. Mask secrets always  
4. Metered probes cached  
5. Key.txt is source of truth (`WS-…/User/Key.txt`)
