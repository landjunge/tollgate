# Tollgate module map

Multi-consumer **secrets, limits, token ledger, routing, auto-update**.

Not “is the string set?” — researched APIs, grades A–F, call/token/char budgets, smart failover.

## Provider docs (source of truth — stop code thrash)

| Layer | Path |
|-------|------|
| Machine | `src/tollgate/distill/<provider>.json` |
| Human index | [`docs/README.md`](README.md) |
| Loader | `tollgate.distill.loader` → `research_for()` / MCP `keys_research` |

**Update rule:** change JSON when docs change; only touch handlers if a *new op type* is needed.

## Layout

```
src/tollgate/
  app_config.py       # keys_app.json — enable, limits, routing, auto_update
  usage_ledger.py     # keys_usage.json — tokens/calls/chars per day
  limits.py           # max_calls_day / max_tokens_day / min_interval
  router.py           # intent → provider chain + failover
  gateway/            # admit, circuit, entry, errors
  chat_route.py       # routed_chat helper
  client.py           # remote HTTP client
  auto_update.py      # background refresh
  service.py          # KeysService facade
  server_v1.py        # FastAPI /v1/*
  mcp.py / mcp_tools.py
  distill/*.json
  deepseek.py brave.py elevenlabs.py openrouter.py …
```

## Config file

| Path | Notes |
|------|--------|
| `$TOLLGATE_HOME/User/keys_app.json` | Preferred |
| `$GNOM_WS/User/keys_app.json` | Gnom-compat |
| `~/.tollgate/User/keys_app.json` | Default |

Auto-created from `DEFAULT_CONFIG` (Google **enabled=false**).

Patch via:

- `POST /v1/config` (HTTP, loopback)
- MCP `keys_config_patch`
- Or edit the JSON on disk

See [COST_LIMITS.md](COST_LIMITS.md).

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
from tollgate import get_keys_service, routed_chat, gateway_search

ks = get_keys_service()
ks.dashboard()
ks.route("free_llm")
routed_chat("hi", intent="free_llm", agent_id="review")
gateway_search("tollgate mcp")
```

## HTTP

```bash
tollgate serve   # http://127.0.0.1:8787
```

| Method | Path |
|--------|------|
| GET | `/v1/health` |
| POST | `/v1/route` |
| POST | `/v1/invoke` |
| GET | `/v1/budget` |
| GET | `/v1/providers` |
| GET/POST | `/v1/config` |

## MCP

See [MCP.md](MCP.md) — `python -m tollgate`, tools `keys_*`.
