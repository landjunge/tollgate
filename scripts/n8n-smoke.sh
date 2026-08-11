#!/usr/bin/env bash
# Smoke the same surfaces n8n workflows / community node hit.
# Usage:
#   export TOLLGATE_HOME=$HOME/WS-gnom-hub-v1   # optional
#   ./scripts/n8n-smoke.sh
#   BASE=http://127.0.0.1:8787 KEY=n8n ./scripts/n8n-smoke.sh
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:8787}"
KEY="${KEY:-n8n}"
AUTH="Authorization: Bearer ${KEY}"
XCK="X-Consumer-Key: ${KEY}"

pass=0
fail=0

check() {
  local name="$1"
  local code="$2"
  local want="${3:-200}"
  if [[ "$code" == "$want" ]]; then
    echo "OK  $name (HTTP $code)"
    pass=$((pass + 1))
  else
    echo "FAIL $name (HTTP $code, want $want)"
    fail=$((fail + 1))
  fi
}

echo "=== n8n surface smoke against $BASE (consumer=$KEY) ==="

code=$(curl -sS -o /tmp/tg-n8n-health.json -w '%{http_code}' \
  -H "$AUTH" -H "$XCK" "$BASE/v1/health" || echo 000)
check "health" "$code"

code=$(curl -sS -o /tmp/tg-n8n-budget.json -w '%{http_code}' \
  -H "$AUTH" -H "$XCK" "$BASE/v1/budget" || echo 000)
check "budget" "$code"
if [[ -f /tmp/tg-n8n-budget.json ]]; then
  python3 -c "import json;d=json.load(open('/tmp/tg-n8n-budget.json')); print('    consumer=', d.get('consumer'), 'allowed=', (d.get('consumer_limits') or {}).get('allowed'))" 2>/dev/null || true
fi

code=$(curl -sS -o /tmp/tg-n8n-route.json -w '%{http_code}' \
  -H "$AUTH" -H "$XCK" -H 'Content-Type: application/json' \
  -d '{"intent":"free_llm","tokens_est":200,"prefer_free":true}' \
  "$BASE/v1/route" || echo 000)
check "route free_llm" "$code"
if [[ -f /tmp/tg-n8n-route.json ]]; then
  python3 -c "import json;d=json.load(open('/tmp/tg-n8n-route.json')); print('    provider=', d.get('provider') or (d.get('route') or {}).get('provider'), 'model=', d.get('model') or (d.get('route') or {}).get('model'))" 2>/dev/null || true
fi

code=$(curl -sS -o /tmp/tg-n8n-chat.json -w '%{http_code}' \
  -H "$AUTH" -H "$XCK" -H 'Content-Type: application/json' \
  -d '{"model":"tollgate/free","messages":[{"role":"user","content":"Reply with exactly: N8N_SMOKE_OK"}],"max_tokens":24}' \
  "$BASE/v1/chat/completions" || echo 000)
check "chat completions" "$code"
if [[ -f /tmp/tg-n8n-chat.json ]]; then
  python3 -c "import json;d=json.load(open('/tmp/tg-n8n-chat.json')); c=(d.get('choices') or [{}])[0].get('message',{}).get('content',''); print('    text=', (c or str(d)[:120])[:100])" 2>/dev/null || true
fi

# Protect: ensure n8n lane has tool limit, then block with tool_calls_est
python3 -m tollgate.cli consumer-budget n8n --max-tool-calls 20 --max-usd-day 1 >/dev/null 2>&1 || true
code=$(curl -sS -o /tmp/tg-n8n-loop.json -w '%{http_code}' \
  -H "$AUTH" -H "$XCK" -H 'Content-Type: application/json' \
  -d '{"model":"tollgate/free","messages":[{"role":"user","content":"loop"}],"max_tokens":8,"tool_calls_est":99}' \
  "$BASE/v1/chat/completions" || echo 000)
# expect deny (402) or error body with max_tool_calls
if [[ "$code" == "402" || "$code" == "429" ]]; then
  check "chat tool_calls_est block" "$code" "$code"
elif [[ -f /tmp/tg-n8n-loop.json ]] && grep -q max_tool_calls /tmp/tg-n8n-loop.json 2>/dev/null; then
  echo "OK  chat tool_calls_est block (body deny, HTTP $code)"
  pass=$((pass + 1))
else
  echo "WARN chat tool_calls_est block (HTTP $code) — set consumer-budget n8n --max-tool-calls 20"
fi

# Certificate surface (Control Room / Prove)
code=$(curl -sS -o /tmp/tg-n8n-cert.json -w '%{http_code}' \
  -H "$AUTH" -H "$XCK" "$BASE/v1/certificate" || echo 000)
check "certificate" "$code"

# search is optional (needs Brave key)
code=$(curl -sS -o /tmp/tg-n8n-search.json -w '%{http_code}' \
  -H "$AUTH" -H "$XCK" -H 'Content-Type: application/json' \
  -d '{"provider":"brave","op":"search","arguments":{"query":"tollgate","count":1},"request_class":"batch","agent_id":"n8n-smoke"}' \
  "$BASE/v1/invoke" || echo 000)
if [[ "$code" == "200" ]]; then
  check "invoke brave search" "$code"
else
  echo "SKIP search (HTTP $code — Brave key may be missing)"
fi

echo ""
echo "Workflows (import in n8n UI):"
echo "  configs/n8n-openai-chat.workflow.json"
echo "  configs/n8n-budget-gate.workflow.json"
echo "  configs/n8n-search.workflow.json"
echo "  configs/n8n-route-invoke.workflow.json"
echo "Community node: n8n-nodes-tollgate/  (see package README)"
echo ""
echo "passed=$pass fail=$fail"
[[ "$fail" -eq 0 ]]
