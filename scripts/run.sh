#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
export TOLLGATE_HOME="${TOLLGATE_HOME:-${GNOM_WS:-$HOME/WS-gnom-hub-v1}}"
PORT="${PORT:-8787}"
HOST="${HOST:-127.0.0.1}"
cd "$ROOT"
echo "Tollgate → http://${HOST}:${PORT}/docs  (TOLLGATE_HOME=$TOLLGATE_HOME)"
exec .venv/bin/uvicorn tollgate.server_v1:app --host "$HOST" --port "$PORT"
