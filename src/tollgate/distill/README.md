# Anbieterspezifikationen als maßgebliche Datenquelle

**Regel:** Funktionen, Limits, Auth und Endpoints kommen aus diesen Specs —
nicht aus ad-hoc Code-Umbau. Code **liest** Destillate; er erfindet sie nicht neu.

| Datei | Inhalt |
|-------|--------|
| `*.json` | Maschinenlesbar (Auth, Endpoints, Ops, Limits, Errors) |
| `docs/keys/providers/*.md` | Menschenlesbar (gleiche Fakten, länger) |
| `loader.py` | `load_distill(id)` / `all_distills()` |

## Wann aktualisieren?

1. Offizielle Dokumentation geändert
2. Prüfung am laufenden Dienst widerspricht der Spezifikation
3. Neues Modell oder neuer Endpunkt

Dann: **nur** JSON (+ optional MD) anfassen, `distilled_at` setzen.
Verarbeitungscode nur ändern, wenn ein **neuer** Vorgangstyp nötig ist.

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
