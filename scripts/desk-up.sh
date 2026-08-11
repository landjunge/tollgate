#!/usr/bin/env bash
# One-shot desk: doctor + Tollgate server for Gnom/n8n
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export TOLLGATE_HOME="${TOLLGATE_HOME:-${GNOM_WS:-$HOME/WS-gnom-hub-v1}}"
export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-8787}"
PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY=python3

cd "$ROOT"
echo "TOLLGATE_HOME=$TOLLGATE_HOME"
"$PY" -m tollgate.cli doctor || true

# consumers for multi-client desk (idempotent-ish: add if missing file)
if [[ ! -f "$TOLLGATE_HOME/User/consumers.json" ]]; then
  echo "creating consumers n8n + gnom (secrets printed once)…"
  "$PY" -m tollgate.cli consumer-add n8n 2>/dev/null || true
  "$PY" -m tollgate.cli consumer-add gnom --admin 2>/dev/null || true
fi

if curl -sf "http://${HOST}:${PORT}/v1/health" >/dev/null 2>&1; then
  echo "already running on ${HOST}:${PORT}"
else
  echo "starting Tollgate on ${HOST}:${PORT}…"
  exec "$PY" -m uvicorn tollgate.server_v1:app --host "$HOST" --port "$PORT"
fi
