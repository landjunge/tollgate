#!/usr/bin/env bash
# Full desk bootstrap: doctor → optional consumers → server → smoke checks
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export TOLLGATE_HOME="${TOLLGATE_HOME:-${GNOM_WS:-$HOME/WS-gnom-hub-v1}}"
export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-8787}"
BASE="http://${HOST}:${PORT}"
PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY=python3
AUTH_MODE="${TOLLGATE_DESK_AUTH:-0}"  # 1 = create consumers if missing

cd "$ROOT"
mkdir -p "$TOLLGATE_HOME/User"

echo "══════════════════════════════════════"
echo " Tollgate desk-ready"
echo " home=$TOLLGATE_HOME"
echo "══════════════════════════════════════"

"$PY" -m tollgate.cli doctor || true

if [[ "$AUTH_MODE" == "1" ]] && [[ ! -f "$TOLLGATE_HOME/User/consumers.json" ]]; then
  echo ""
  echo "→ Creating consumers (secrets shown ONCE — store them)…"
  "$PY" -m tollgate.cli consumer-add n8n
  "$PY" -m tollgate.cli consumer-add gnom --admin
  echo "Set n8n API key to n8n:<secret> and Gnom TOLLGATE_CONSUMER=gnom:<secret>"
fi

if ! curl -sf "$BASE/v1/health" >/dev/null 2>&1; then
  echo ""
  echo "→ Starting server $BASE …"
  nohup "$PY" -m uvicorn tollgate.server_v1:app --host "$HOST" --port "$PORT" \
    > /tmp/tollgate-desk.log 2>&1 &
  echo $! > /tmp/tollgate-desk.pid
  for i in 1 2 3 4 5 6 7 8 9 10; do
    curl -sf "$BASE/v1/health" >/dev/null 2>&1 && break
    sleep 0.5
  done
fi

echo ""
bash "$ROOT/scripts/desk-check.sh"

echo ""
echo "══════════════════════════════════════"
echo " Ready — Protect · Route · Prove"
echo "  Dashboard: $BASE/dashboard"
echo "  OpenAPI:   $BASE/docs"
echo "  Control:   $BASE/v1/control"
echo "  Metrics:   $BASE/metrics"
echo "  n8n base:  $BASE/v1  model=tollgate/free"
echo "  Gnom:      export TOLLGATE_URL=$BASE"
echo "  Log:       /tmp/tollgate-desk.log"
echo "  Stop:      kill \$(cat /tmp/tollgate-desk.pid 2>/dev/null)"
echo ""
echo "  Next (2 min):"
echo "    tollgate consumer-budget n8n --max-usd-day 2 --max-requests-minute 30 --max-tool-calls 15"
echo "    tollgate chaos test opencode_zen --requests 5"
echo "    tollgate resilience"
echo "  Guide: docs/GETTING_STARTED.md"
echo "══════════════════════════════════════"
