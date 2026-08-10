# Provider distillates (source of truth)

**Regel:** Funktionen, Limits, Auth und Endpoints kommen aus diesen Specs —  
nicht aus ad-hoc Code-Umbau. Code **liest** Destillate; er erfindet sie nicht neu.

| Datei | Inhalt |
|-------|--------|
| `*.json` | Maschinenlesbar (Auth, Endpoints, Ops, Limits, Errors) |
| `docs/keys/providers/*.md` | Menschenlesbar (gleiche Fakten, länger) |
| `loader.py` | `load_distill(id)` / `all_distills()` |

## Wann updaten?

1. Offizielle Docs geändert  
2. Live-Probe widerspricht Spec  
3. Neues Modell / neuer Endpoint  

Dann: **nur** JSON (+ optional MD) anfassen, `distilled_at` setzen.  
Handlers nur anfassen, wenn ein **neuer** Op-Typ nötig ist.

## Schema (jedes `*.json`)

```text
id, title, distilled_at, sources[]
auth { type, header|query, env[], key_prefix? }
base_urls { default, … }
endpoints[] { id, method, path, cost, purpose }
models / model_notes
limits { … }
errors { code → meaning }
ops[] { name, maps_to, args, notes }   ← Hub/MCP functions
gotchas[]
headers_out[]  # e.g. rate limit headers
hub { probe, capabilities[], default_model? }
```
