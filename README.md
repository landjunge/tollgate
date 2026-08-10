# Tollgate

**Pay the toll — or don't call.**

Multi-consumer **API admission + key router** for AI agents, n8n, and local desks.

- Budgets (calls / tokens / chars / USD)
- Circuit breakers + error taxonomy
- Distill-backed provider specs (not code thrash)
- Google/Gemini **disabled by default** (bill-shock guard)
- HTTP `/v1/*` + MCP stdio
- Shared control plane for **Gnom, n8n, Cursor, other agents**

## Quick start

```bash
cd tollgate
python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"

# Point at secrets (Gnom WS still works)
export TOLLGATE_HOME="$HOME/WS-gnom-hub-v1"   # or ~/.tollgate with User/Key.txt
# or: export GNOM_WS="$HOME/WS-gnom-hub-v1"

./scripts/run.sh
# → http://127.0.0.1:8787/docs
```

### HTTP (multi-consumer)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/v1/health` | Liveness + circuits |
| POST | `/v1/route` | intent → provider/model |
| POST | `/v1/invoke` | admit + call + meter |
| GET | `/v1/budget` | remaining limits |
| GET | `/v1/providers` | inventory grades |

Header: `X-Consumer-Key: n8n` (placeholder until consumer secrets land).

### MCP

```bash
PYTHONPATH=src TOLLGATE_HOME=… .venv/bin/python -m tollgate
```

See `configs/mcp-tollgate.example.json` and `docs/MCP.md`.

## Config

| File | Role |
|------|------|
| `$TOLLGATE_HOME/User/Key.txt` | Provider secrets |
| `$TOLLGATE_HOME/User/keys_app.json` | Limits, routing, cost_guard |
| `$TOLLGATE_HOME/User/keys_usage.json` | Daily ledger |

## Docs

- [VISION.md](docs/VISION.md)
- [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [COST_LIMITS.md](docs/COST_LIMITS.md)
- [N8N.md](docs/N8N.md)

## Relation to Gnom-Hub

Gnom is a **client**. This repo is the **product**.  
Legacy code may still live briefly under `gnom-hub-v1/src/gnom_hub/keys` until Gnom depends on `tollgate` as a package.
