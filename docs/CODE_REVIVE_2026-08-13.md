# Code revive — complete (2026-08-13)

**Not a rewrite.** Full hygiene after modular slices M8–M11, under architect rules.

## Intent

| Do | Don’t |
|----|--------|
| Fix regressions from extraction | Big Clean Architecture |
| soft_fail instead of silent `pass` | Touch admit core |
| Dead imports / NameError | New features |
| Keep public API | Microservice split |
| Fail-closed on Protect scope errors | Adapter zoo / entry.py split |

## Pass 1 (team hygiene)

1. **Bug:** dashboard still called `el_mod` after M9 → **NameError** if elevenlabs ready — `get_ops("elevenlabs")["budget"]`
2. **Observability:** `package_deny`, router health, free_policy, inspect kwargs → `soft_fail`
3. **Lint:** unused imports (`catalog.field`, `control_plane.json`, `filelock.os`, `metrics.Any`, unused `RequestClass` in router, dead `audit_pass`)

## Pass 2 (complete)

### P0 bugs

1. **`KeysService.diagnose(live=True)`** still called `openrouter_mod.credits()` after M9 → **NameError** on every live diagnose (`tollgate doctor --live`). Now `get_ops("openrouter")["credits"]` + `soft_fail`.
2. **`GET /` duplicate key `"product"`** — last write won (`docs/PRODUCT.md` overwrote `"Tollgate"`). Split: `"product": "Tollgate"` + `"product_doc": "docs/PRODUCT.md"`.
3. **`tollgate doctor --live`** read `level`/`message` from diagnose issues that use `severity`/`issue` — live rows always `warn` and dumped the whole dict. Now mapped.
4. **`audit.query_audit`** called non-existent `read_audit` and `list(dict)` (keys, not events). Pass-through to `audit_log.query_audit`.

### Protect fail-closed

- `chat_route` / `chat_stream` scope check: exception was **silent pass** (fail-open). Now deny with `protection=scope`.

### Observability → `soft_fail`

Stream rates/usage/audit · chaos alerts/audit/keys · freeze alerts/audit · control plane extras · doctor freeze/chaos · config parse/write/validate · identity list · serve banner · provider health · cost distill · secrets env write · OpenAI models inventory.

**Left silent on purpose:** `soft_fail` logger/audit-nested `pass`, fail-closed ledger/admit *decisions*.

## Pass 3 (hot-path log, no audit spam)

- `soft_fail(..., audit=False)` — count + log, skip `audit.jsonl`
- Wired: `/metrics` extras, process bootstrap (`server_v1` / MCP), `append_audit` write fail, ledger usage/corrupt audit, circuit load/save
- Snapshot post-import cache clear → `soft_fail`
- Resilience: dead `min(reliability, reliability)` / unused `degraded` removed
- Admit **alerts only** (not decisions) → `soft_fail` — deny/allow unchanged

### Dead weight

- unused: `provider_scaffold.Path`, `secrets.project_root`, `resilience.consumers` / `healthy`, `schema.remaining`
- stale scaffold hint `KeysService._OPS` → `provider_ops/registry.py`
- f-strings without placeholders (`provider_scaffold`, `report`)

## Verify

```bash
pytest -q          # 204
tollgate doctor    # PASS / production readiness
```

## Pass 4 (auth fail-closed + version truth)

1. **`consumers.json` parse fail-open:** unreadable file became empty → open mode. Now `_corrupt` + `auth_required` + `verify_consumer` deny. `consumer-add` still recovers. Doctor reports `consumers_corrupt`.
2. **Stale version fallbacks** `0.3.4` / `0.3.7` in alerts/report → `1.0.12`. `GET /v1/health` and FastAPI `version` use `__version__`.
3. Circuit config load → `soft_fail(..., audit=False)`.

## Pass 5 (config freeze fail-closed)

**`keys_app.json` parse fail-open:** junk file merged with defaults → freeze OFF, custom envelopes gone.  
Now `_corrupt` + `is_frozen()` True (env override still wins). Admit denies via existing freeze path. `save_config` strips the marker. Doctor reports `keys_app_corrupt`. Missing file still writes defaults (not corrupt).

## Pass 6 (circuits persist + doctor honesty)

1. **`circuits.json` parse fail-open:** junk file left breakers **closed** → traffic allowed. Now `allow()` is False until `circuits reset --all` rewrites a valid file. Doctor: `circuits_corrupt`.
2. **Readiness lies:** `consumers.json` corrupt counted as Authentication PASS (`required=True`). Now FAIL. `keys_app_corrupt` is not a generic “unfreeze” hint.

## Team close (R1)

Architect review of the revive tree (2026-08-13):

- Protect still does not import Route/router/failover
- Admit decisions unchanged; freeze/circuit/auth fail-closed sit in the modules that already owned those questions
- `circuits_corrupt` lives on the **Route** facade (doctor reads `tollgate.route`, not circuit internals)
- Public API not broken; extra keys are additive
- **Stop here.** Next code only from desk pain (Owner go/no-go). Not another hygiene sweep.

### M6b (team, dual-path)

`chat_stream` no longer copies prove/admit/rates. It calls `_stage_prove_availability` / `_stage_protect_admit` / `_stage_protect_rates` in `entry.py`. Synthetic hops already used `gateway_call`. Reserve before first SSE byte stays in stream (no entry stage for that).

## Still out of scope (pain-driven later)

- Full ProviderAdapter classes per provider
- entry.py file split
- admit **decisions** (freeze/limits/circuit logic untouched; only alert wrappers logged)

*Team rule: each module still answers one question. Revive does not invent new questions.*
