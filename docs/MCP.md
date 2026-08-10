# Tollgate — MCP anbindung

**Product:** Tollgate (future repo `tollgate`)

Über **drei MCP-Wege** erreichbar.

## 1) Stdio MCP Server (Cursor / Claude Desktop / Agents)

```bash
cd /Users/landjunge/gnom-hub-v1
PYTHONPATH=src GNOM_WS=/Users/landjunge/WS-gnom-hub-v1 \
  .venv/bin/python -m gnom_hub.keys.mcp
```

### Cursor `mcp.json` Beispiel

```json
{
  "mcpServers": {
    "tollgate": {
      "command": "/Users/landjunge/gnom-hub-v1/.venv/bin/python",
      "args": ["-m", "gnom_hub.keys.mcp"],
      "env": {
        "PYTHONPATH": "/Users/landjunge/gnom-hub-v1/src",
        "GNOM_WS": "/Users/landjunge/WS-gnom-hub-v1"
      }
    }
  }
}
```

Gleich mit `python -m gnom_hub.keys`. Config-Beispiel: `configs/mcp-gnom-keys.example.json` (server id `tollgate`).

### Tools (stdio)

| Tool | Zweck |
|------|--------|
| `keys_dashboard` | Grades, usage, smart route |
| `keys_diagnose` | Issues + actions |
| `keys_status` | Inventory / ein Provider |
| `keys_route` | Intent → Provider + fallbacks |
| `keys_preflight` | Spend-Gate |
| `keys_usage` | Token/Call-Ledger heute |
| `keys_config_get` / `keys_config_patch` | Config |
| `keys_limits` | Restbudget Provider |
| `keys_auto_update` | start/stop/once |
| `keys_call` | generisch |
| `keys_web_search` | Brave + Limits |
| `keys_elevenlabs_budget` | TTS-Floor |
| `keys_zen_chat` | OpenCode Zen free chat |
| `keys_research` | Offline-Research |

### Resources

| URI | Inhalt |
|-----|--------|
| `keys://app/config` | keys_app.json |
| `keys://app/usage` | keys_usage.json |
| `keys://app/dashboard` | Dashboard snapshot |
| `keys://app/research` | Research notes |

---

## 2) Hub HTTP MCP-lite (läuft mit Gnom :8080)

| Endpoint | |
|----------|--|
| `GET /api/mcp/tools` | alle Hub-Tools inkl. keys_* |
| `GET /api/mcp/tools?scope=keys` | nur Keys-Tools |
| `GET /api/mcp/keys/tools` | dasselbe |
| `POST /api/mcp/keys/call` | `{ "name": "keys_route", "arguments": {…} }` |
| `GET /api/mcp/keys/resources` | Resources list |
| `GET /api/mcp/keys/resources/read?uri=keys://app/usage` | Resource read |
| `POST /api/mcp` | JSON-RPC; mit `"params":{"scope":"keys"}` nur Keys |

Beispiel:

```bash
curl -s http://127.0.0.1:8080/api/mcp/keys/tools | jq '.tools[].name'

curl -s -X POST http://127.0.0.1:8080/api/mcp/keys/call \
  -H 'Content-Type: application/json' \
  -d '{"name":"keys_route","arguments":{"intent":"free_llm"}}'
```

---

## 3) Hub ToolRegistry (Pipeline / Telegram / SPA)

Beim Hub-Start: `register_keys_mcp_on_registry(self.tools)`  
→ alle keys_* Tools erscheinen in `/api/mcp/tools` und `/api/tools/call`.

---

## Token-Zählung über MCP

`keys_zen_chat`, `keys_web_search`, `keys_call` laufen durch `KeysService.call` →  
**Limits + usage_today + limits_remaining** in der Antwort.
