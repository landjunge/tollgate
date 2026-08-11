# Tollgate docs

**Repo:** https://github.com/landjunge/tollgate  
**Package path for provider truth:** `src/tollgate/distill/*.json`

| Doc | Topic |
|-----|--------|
| [VISION.md](VISION.md) | Product lock, multi-consumer |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 7 layers, circuits, taxonomy |
| [COST_LIMITS.md](COST_LIMITS.md) | Google off, budgets, `/v1/config` |
| [MCP.md](MCP.md) | stdio MCP + HTTP `/v1/*` |
| [N8N.md](N8N.md) | n8n as consumer |
| [KEYS_MODULE.md](KEYS_MODULE.md) | Module map (legacy name) |
| [PORTABLE.md](PORTABLE.md) | USB stick / no host paths |

## Rule (no more code thrash)

| Do | Don't |
|----|--------|
| Update distill JSON when APIs change | Invent endpoints inside random `.py` files |
| Add `ops[]` for new MCP functions | Copy-paste limits into 5 modules |
| Bump `distilled_at` | Rewrite router/service for every doc tweak |

## Providers

| ID | Distill JSON |
|----|----------------|
| deepseek | `src/tollgate/distill/deepseek.json` |
| worker | `src/tollgate/distill/worker.json` |
| brave | `src/tollgate/distill/brave.json` |
| elevenlabs | `src/tollgate/distill/elevenlabs.json` |
| openrouter | `src/tollgate/distill/openrouter.json` |
| nvidia | `src/tollgate/distill/nvidia.json` |
| minimax | `src/tollgate/distill/minimax.json` |
| opencode_zen | `src/tollgate/distill/opencode_zen.json` |
| google | `src/tollgate/distill/google.json` (high_risk, off by default) |
| telegram | `src/tollgate/distill/telegram.json` |

```python
from tollgate.distill.loader import load_distill, research_view, ops_for

spec = load_distill("brave")
for op in ops_for("brave"):
    print(op["name"], "→", op["maps_to"])
```
