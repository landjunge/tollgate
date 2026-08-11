# Desk runbook (Gnom + n8n + Tollgate)

## One command

```bash
export TOLLGATE_HOME=$HOME/WS-gnom-hub-v1
cd ~/tollgate
./scripts/desk-ready.sh
# optional auth: TOLLGATE_DESK_AUTH=1 ./scripts/desk-ready.sh
```

## Clients

| Client | Config |
|--------|--------|
| **Gnom** | Hub auto-pins `TOLLGATE_HOME`. Optional: `TOLLGATE_URL=http://127.0.0.1:8787` |
| **n8n** | OpenAI Base `http://127.0.0.1:8787/v1`, Key `n8n`, Model `tollgate/free` |
| **n8n Docker** | Base `http://host.docker.internal:8787/v1` |
| **Anthropic SDK** | Base `http://127.0.0.1:8787`, Key `desk` → `POST /v1/messages` ([ANTHROPIC.md](ANTHROPIC.md)) |
| **Import** | `configs/n8n-openai-chat.workflow.json` |

## Checks

```bash
./scripts/desk-check.sh      # health + free chat
./scripts/live_smoke.sh      # route + chat
tollgate doctor
curl -s localhost:8787/metrics | head
# optional lane caps (n8n vs gnom):
# tollgate consumer-budget n8n --max-usd-day 0.5 --max-calls-day 200
# curl -s localhost:8787/v1/budget -H 'X-Consumer-Key: n8n'
```

## Stop

```bash
kill $(cat /tmp/tollgate-desk.pid 2>/dev/null)
# or: pkill -f 'uvicorn tollgate.server_v1'  (avoid matching this shell)
```
