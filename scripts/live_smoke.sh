#!/usr/bin/env bash
# Live smoke against a running Tollgate (or starts one).
# Usage: TOLLGATE_HOME=… ./scripts/live_smoke.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export TOLLGATE_HOME="${TOLLGATE_HOME:-${GNOM_WS:-$HOME/WS-gnom-hub-v1}}"
BASE="${TOLLGATE_URL:-http://127.0.0.1:8787}"
PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY=python3

echo "doctor…"
"$PY" -m tollgate.cli doctor || true

if ! curl -sf "$BASE/v1/health" >/dev/null 2>&1; then
  echo "starting server on :8787…"
  nohup "$PY" -m uvicorn tollgate.server_v1:app --host 127.0.0.1 --port 8787 \
    > /tmp/tollgate-live-smoke.log 2>&1 &
  sleep 2
fi

echo "route free_llm…"
curl -sS -X POST "$BASE/v1/route" \
  -H "Content-Type: application/json" -H "X-Consumer-Key: live-smoke" \
  -d '{"intent":"free_llm","tokens_est":128}' | "$PY" -m json.tool | head -30

echo "chat completions…"
curl -sS -X POST "$BASE/v1/chat/completions" \
  -H "Content-Type: application/json" -H "Authorization: Bearer live-smoke" \
  -d '{"model":"tollgate/free","messages":[{"role":"user","content":"Reply with exactly: TOLL_OK"}],"max_tokens":32}' \
  | "$PY" -c "import sys,json;d=json.load(sys.stdin);print(d.get('choices',[{}])[0].get('message',{}).get('content') if 'choices' in d else d)"

echo "OK — set n8n OpenAI base to $BASE/v1"
