# Scale & future-proofing

Two different questions:

| | Meaning | Tollgate stance |
|--|---------|-----------------|
| **Scale** | more load | Single-host desk first; shared file state for multi-worker |
| **Future-proof** | world changes | Distill data + `/v1` + tests, not code thrash |

## Scale (honest limits)

**Designed for:** one host, several local consumers (Gnom, n8n, Cursor).

| Component | Storage | Multi-worker safe? |
|-----------|---------|-------------------|
| Ledger (`keys_usage.json`) | file + **process lock** | yes (exclusive RMW) |
| Circuits (`circuits.json`) | file + **process lock** | yes (shared open/closed) |
| Response cache | in-memory | **no** (per process OK) |
| Config / secrets | files | read-mostly |

**Not designed for (yet):** multi-host load balancer with independent budgets. That needs Redis/Postgres for envelopes + circuits, or you double-spend the day cap.

**Before “production multi-consumer”:** run concurrent ledger writes (CI: `tests/test_concurrency.py`) and prefer **one** uvicorn worker unless you accept per-worker cache misses.

```bash
# Prefer for correct shared circuits/budget semantics:
uvicorn tollgate.server_v1:app --host 127.0.0.1 --port 8787 --workers 1
```

Multi-worker is OK for throughput if all workers share the same `TOLLGATE_HOME` (circuits + ledger are on disk). Response cache will not be shared.

## Future-proofing

### Distill `schema_version`

Every provider JSON has `"schema_version": 1`. Loader defaults missing → 1.  
`validate_distill` rejects versions below min or above `CURRENT_SCHEMA_VERSION`.

When the shape must change: bump `CURRENT_SCHEMA_VERSION`, add migration in loader, keep old files readable for one minor.

### HTTP versioning

| Rule | Detail |
|------|--------|
| Current | `/v1/*` is the stable contract |
| Breaking change | add `/v2/*`, keep `/v1` ≥ 1 minor |
| Deprecation | document in CHANGELOG + `Sunset` header later if needed |
| Guardrails | `tests/test_contract_v1.py`, `tests/test_openai_compat.py` |

OpenAI drop-in (`/v1/chat/completions`) is part of the v1 surface.

### High-risk providers

**Config-driven:** `cost_guard.high_risk_providers` + distill `high_risk` + CLI `tollgate high-risk add …` — not Google-only hardcode.

### Dependencies

Dependabot (`.github/dependabot.yml`) opens weekly pip PRs.

### What we deliberately do not store

Agent memory / transcripts — see `ops_boundary` and ARCHITECTURE “cache ≠ memory”.

## Checklist: “ready for more consumers”

- [x] Consumer auth (hash / open mode)
- [x] OpenAI drop-in
- [x] Shared circuits on disk
- [x] Locked ledger RMW
- [x] Contract + concurrency tests
- [ ] Real multi-process load soak (optional local)
- [ ] Redis only if multi-host budgets required
