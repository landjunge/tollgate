# Operations: deploy, doctor, auto-maintenance

## Deploy

| Path | Command |
|------|---------|
| Docker | `docker compose up -d` |
| USB | `./scripts/portable-setup.sh && ./scripts/run.sh` |
| Dev | `pip install -e . && tollgate serve` |

First command after install: **`tollgate doctor`**.

## Audit trail (who was denied)

Append-only file: `$TOLLGATE_HOME/User/audit.jsonl` (never rewritten).

```bash
tollgate audit --event admit_deny --limit 20
tollgate audit --consumer n8n
tollgate audit --summary
curl -s 'http://127.0.0.1:8787/v1/audit?event=admit_deny&limit=20'
curl -s 'http://127.0.0.1:8787/v1/audit?summary=true'
```

Also on the control plane: `GET /v1/control` → `recent_denies` + dashboard table.

## Metrics auth (v0.3+)

| Mode | Behavior |
|------|----------|
| Open desk (no consumers) | `GET /metrics` open |
| Auth mode (`consumers.json` / `TOLLGATE_REQUIRE_AUTH=1`) | requires valid consumer key |
| `TOLLGATE_METRICS_TOKEN=…` | requires `X-Metrics-Token` or `Authorization: Bearer <token>` |
| `TOLLGATE_METRICS_PUBLIC=1` | always open (explicit opt-out) |

```bash
# Prometheus scrape with dedicated token
export TOLLGATE_METRICS_TOKEN=scrape-secret
curl -H "X-Metrics-Token: scrape-secret" http://127.0.0.1:8787/metrics
```

Still prefer binding loopback or a reverse proxy for multi-host.

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
- **Old `keys_app.json` without a `circuits` block remains valid** — defaults apply
  (`jitter` 0.8–1.2, `cooldown_s` 30, `hard_cooldown_s` 300, threshold 5)

## Auto-maintenance (what is automatic)

| Mechanism | Behavior |
|-----------|----------|
| Day ledger rollover | On next read/write if `day != today` — **no cron** |
| Circuit half-open | Auto after jittered cooldown (`circuits.jitter_min`–`jitter_max`); canary success closes |
| Hard circuit open | `AUTH_DEAD` etc. elevates that circuit’s `cooldown_s` to at least `hard_cooldown_s` (default 300s) and **persists** it in `circuits.json`. Soft failures after recovery may still use the elevated cooldown until the row is cleared/reset — intentional (dead keys stay cold) |
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
