# Keys provider documentation (distilled)

**Source of truth for functions:**  
`src/gnom_hub/keys/distill/*.json`

Human-readable companions live here under `providers/`.

## Rule (no more code thrash)

| Do | Don't |
|----|--------|
| Update distill JSON when APIs change | Invent endpoints inside random .py files |
| Add `ops[]` for new Hub/MCP functions | Copy-paste limits into 5 modules |
| Bump `distilled_at` | Rewrite router/service for every doc tweak |
| Keep MD in sync optionally | Hand-edit `research_notes.py` facts |

## Providers

| ID | Distill JSON | Topic |
|----|--------------|--------|
| deepseek | `distill/deepseek.json` | OpenAI-compat chat, concurrency |
| worker | `distill/worker.json` | Same API, worker key |
| brave | `distill/brave.json` | Search + rate headers |
| elevenlabs | `distill/elevenlabs.json` | Credits / TTS floor |
| openrouter | `distill/openrouter.json` | Credits, :free caps, key chain |
| nvidia | `distill/nvidia.json` | NIM catalog |
| minimax | `distill/minimax.json` | Regions, error 2049 |
| opencode_zen | `distill/opencode_zen.json` | Free models, Cloudflare UA |
| telegram | `distill/telegram.json` | Optional bot |

## How handlers use this

```python
from gnom_hub.keys.distill.loader import load_distill, research_view, ops_for

spec = load_distill("brave")
for op in ops_for("brave"):
    print(op["name"], "→", op["maps_to"])
```

MCP: `keys_research` / `keys_call op=research` returns `research_view(id)`.

## Updating a provider

1. Open official docs (listed in `sources[]`)
2. Edit **only** `distill/<id>.json`
3. Optionally refresh `docs/keys/providers/<id>.md`
4. Run: `pytest tests/test_keys_distill.py -q`
5. Touch Python handlers **only** if a new op type is required
