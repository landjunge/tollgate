#!/usr/bin/env bash
# Quick desk health: Tollgate + optional Gnom env tips
set -euo pipefail
BASE="${TOLLGATE_URL:-http://127.0.0.1:8787}"
BASE="${BASE%/v1}"
export TOLLGATE_HOME="${TOLLGATE_HOME:-${GNOM_WS:-$HOME/WS-gnom-hub-v1}}"

echo "== Tollgate $BASE =="
if ! curl -sf "$BASE/v1/health" >/dev/null; then
  echo "DOWN — start: cd ~/tollgate && TOLLGATE_HOME=$TOLLGATE_HOME ./scripts/desk-up.sh"
  exit 1
fi
curl -sS "$BASE/v1/health" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('ok', d.get('ok'), 'version', d.get('version'))
print('data_home', (d.get('portable') or {}).get('data_home'))
print('auth_required', (d.get('auth') or {}).get('required'))
"
echo
echo "== OpenAI chat free =="
curl -sS -X POST "$BASE/v1/chat/completions" \
  -H "Authorization: Bearer desk-check" \
  -H "Content-Type: application/json" \
  -d '{"model":"tollgate/free","messages":[{"role":"user","content":"Reply with: DESK_OK"}],"max_tokens":16}' \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('choices',[{}])[0].get('message',{}).get('content') if 'choices' in d else d)"
echo
echo "== n8n hint =="
echo "Base URL: $BASE/v1   Key: n8n   Model: tollgate/free"
echo "Import: configs/n8n-openai-chat.workflow.json"
echo "== Gnom hint =="
echo "export TOLLGATE_URL=$BASE"
echo "export TOLLGATE_HOME=$TOLLGATE_HOME"
echo "export GNOM_WS=$TOLLGATE_HOME"
