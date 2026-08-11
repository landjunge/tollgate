# Operations: deploy, doctor, auto-maintenance

## Deploy

| Path | Command |
|------|---------|
| Docker | `docker compose up -d` |
| USB | `./scripts/portable-setup.sh && ./scripts/run.sh` |
| Dev | `pip install -e . && tollgate serve` |

First command after install: **`tollgate doctor`**.

## Doctor

```bash
tollgate doctor           # paths, Key.txt, config schema, high-risk caps
tollgate doctor --live    # + KeysService.diagnose live probes
tollgate doctor --json
```

Exit code 1 if errors (e.g. missing Key.txt, high-risk enabled without `$` cap).

## Config validation

- Pydantic model: `config_validate.KeysAppConfig`
- On `load_config` / `tollgate serve` / server bootstrap
- `TOLLGATE_STRICT_CONFIG=1` → refuse start on semantic errors

## Auto-maintenance (what is automatic)

| Mechanism | Behavior |
|-----------|----------|
| Day ledger rollover | On next read/write if `day != today` — **no cron** |
| Circuit half-open | Auto after jittered cooldown; canary success closes |
| Soft budget + anomaly burn | Soft warn + optional webhook — **does not change config** |
| `tollgate suggest` | Proposes routing/spend tweaks — **human applies** |
| Dependabot | Weekly pip PRs on GitHub |
| Response cache | TTL free/batch only |

## What never auto-applies

- Budget limits, high-risk enables, routing order  
- Distill JSON rewrites from “AI scrape” without review  

KI/Heuristik **schlägt vor**, Mensch bestätigt — sonst bricht das Audit-Versprechen.

## Related

- [STABILITY.md](STABILITY.md) multi-worker  
- [OPENAI.md](OPENAI.md) drop-in clients  
- MCP `keys_diagnose` / `keys_auto_update` for agents  
