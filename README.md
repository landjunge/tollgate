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
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

# Desk: ~/.tollgate  ·  USB stick: sibling WS-tollgate or TOLLGATE_HOME
# export TOLLGATE_HOME=/path/to/WS-tollgate
# export TOLLGATE_PORTABLE=1   # force stick layout off-USB

./scripts/run.sh
# → http://127.0.0.1:8787/docs
```

### USB / portable

```bash
./scripts/portable-setup.sh   # creates ../WS-tollgate/User + optional .venv
./scripts/run.sh              # auto-detects /Volumes /media /mnt
```

See [docs/PORTABLE.md](docs/PORTABLE.md). No machine-local `/Users/…` paths required.

### HTTP (multi-consumer)

Kurzüberblick — **aktuelle Signaturen:** `http://127.0.0.1:8787/docs` (OpenAPI/Swagger, SSoT).

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/v1/health` | Liveness + portable + auth mode |
| GET | `/v1/auth` | Whether consumer secrets are required |
| POST | `/v1/route` | intent → provider/model |
| POST | `/v1/invoke` | admit + call + meter |
| GET | `/v1/budget` | remaining limits |
| GET | `/v1/providers` | inventory grades (masked) |
| GET/POST | `/v1/config` | policy (admin when auth on) |

Header: `X-Consumer-Key: n8n` (open mode) or `n8n:<secret>` after `tollgate consumer-add n8n`.

Contract tests in `tests/test_contract_v1.py` fire these paths in CI.

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

Defaults: portable/USB → sibling `WS-tollgate` or colocated `User/`; desk → `~/.tollgate`.  
Compat: `GNOM_WS` still works.

## Docs

- [VISION.md](docs/VISION.md)
- [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [COST_LIMITS.md](docs/COST_LIMITS.md)
- [MCP.md](docs/MCP.md)
- [N8N.md](docs/N8N.md)
- [PORTABLE.md](docs/PORTABLE.md)

```bash
./scripts/check_docs_drift.sh    # old paths/ports in docs
./scripts/check_migration.sh     # green/yellow/red per doc
pytest -q                        # includes contract + distill schema
```

## Relation to Gnom-Hub

Gnom is a **client**. This repo is the **product**.

```python
from tollgate import routed_chat, gateway_search, get_keys_service

routed_chat("hello", intent="free_llm", agent_id="gnom")
gateway_search("brave through tollgate")
```

Gnom installs Tollgate via git dependency and routes Brave / budgets / free LLM through this gateway.
