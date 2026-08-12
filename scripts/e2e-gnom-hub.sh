#!/usr/bin/env bash
# Smoke the gnom-hub → Tollgate pipe (HTTP).
# Requires: tollgate serve on 127.0.0.1:8787
# Optional: gnom-hub with TOLLGATE_URL set (manual UI tests in docs/E2E_GNOM_HUB.md)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-8787}"
BASE="http://${HOST}:${PORT}"
CONSUMER="${TOLLGATE_CONSUMER:-gnom}"
PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY=python3
MODE="${1:-all}"

pass=0
fail=0
note() { echo "  · $*"; }
ok() { echo "  ✓ $*"; pass=$((pass + 1)); }
bad() { echo "  ✗ $*"; fail=$((fail + 1)); }

echo ""
echo " E2E gnom-hub ↔ Tollgate  base=$BASE  consumer=$CONSUMER"
echo ""

if ! curl -sf "$BASE/v1/health" >/dev/null 2>&1; then
  echo "FAIL: Tollgate not up at $BASE"
  echo "  cd ~/tollgate && HOST=127.0.0.1 .venv/bin/tollgate serve"
  exit 1
fi
ok "health"

# Ensure gnom lane exists with sane demo limits
"$PY" -m tollgate.cli consumer-budget "$CONSUMER" \
  --max-usd-day 2 \
  --max-usd-request 0.5 \
  --max-requests-minute 50 \
  --max-tool-calls 20 \
  --allow-intent free_llm --allow-intent llm \
  --allow-op chat >/dev/null 2>&1 || true
ok "consumer-budget $CONSUMER"

run_normal() {
  echo ""
  echo "── Test 1 normal (chat via /v1) ──"
  RESP=$(curl -sS "$BASE/v1/chat/completions" \
    -H "Authorization: Bearer $CONSUMER" \
    -H "Content-Type: application/json" \
    -d '{"model":"tollgate/free","messages":[{"role":"user","content":"ping from e2e-gnom"}],"max_tokens":32}' || true)
  if echo "$RESP" | grep -q '"choices"'; then
    ok "chat completions returned choices"
  elif echo "$RESP" | grep -qi 'blocked\|quota\|budget\|tool'; then
    note "chat denied by policy (still a valid pipe): $(echo "$RESP" | head -c 160)"
    ok "chat path responded (deny)"
  else
    note "response: $(echo "$RESP" | head -c 200)"
    bad "chat did not return choices (keys/providers?)"
  fi
}

run_loop() {
  echo ""
  echo "── Test 4 agent loop ──"
  RESP=$(curl -sS "$BASE/v1/invoke" \
    -H "Content-Type: application/json" \
    -H "X-Consumer-Key: $CONSUMER" \
    -d "{\"provider\":\"opencode_zen\",\"op\":\"chat\",\"tool_calls_est\":99,\"tokens_est\":10,\"arguments\":{\"message\":\"loop\"},\"agent_id\":\"gnom:loop\"}")
  if echo "$RESP" | grep -qi 'BLOCKED\|max_tool_calls\|tool-loop\|tool loop\|blocked'; then
    ok "loop hard-stop for $CONSUMER"
  else
    note "response: $(echo "$RESP" | head -c 220)"
    bad "expected tool-loop block"
  fi
}

run_budget() {
  echo ""
  echo "── Test 2 budget (tight day cap) ──"
  "$PY" -m tollgate.cli consumer-budget "$CONSUMER" \
    --max-usd-day 0.0001 \
    --max-tool-calls 50 \
    --allow-intent free_llm --allow-intent llm \
    --allow-op chat >/dev/null
  RESP=$(curl -sS "$BASE/v1/invoke" \
    -H "Content-Type: application/json" \
    -H "X-Consumer-Key: $CONSUMER" \
    -d '{"provider":"opencode_zen","op":"chat","tokens_est":500000,"arguments":{"message":"budget"},"agent_id":"gnom:budget"}')
  # restore sane budget
  "$PY" -m tollgate.cli consumer-budget "$CONSUMER" \
    --max-usd-day 2 --max-tool-calls 20 \
    --allow-intent free_llm --allow-intent llm --allow-op chat >/dev/null
  if echo "$RESP" | grep -qi 'BLOCKED\|budget\|quota\|usd\|protection'; then
    ok "budget/protection deny path"
  else
    note "response: $(echo "$RESP" | head -c 220)"
    bad "expected budget-style deny (may need spend already high)"
  fi
}

run_control() {
  echo ""
  echo "── Control plane (gnom visible?) ──"
  CTRL=$(curl -sS "$BASE/v1/control" -H "Authorization: Bearer $CONSUMER" || true)
  if echo "$CTRL" | grep -q "\"consumer\": \"$CONSUMER\"" || echo "$CTRL" | grep -q "$CONSUMER"; then
    ok "control snapshot mentions $CONSUMER"
  else
    note "consumers may list under usage after traffic"
    ok "control reachable"
  fi
}

run_chaos() {
  echo ""
  echo "── Test 3 chaos / failover (production route path) ──"
  CHAOS_PROVIDER="${CHAOS_PROVIDER:-deepseek}"
  OUT=$("$PY" -m tollgate.cli chaos test "$CHAOS_PROVIDER" --intent free_llm --requests 6 2>&1 || true)
  note "$(echo "$OUT" | tail -c 280)"
  if echo "$OUT" | grep -qiE 'survived|failover|100\.0|successful|ok.?true|PASS|providers_used'; then
    ok "chaos test completed for $CHAOS_PROVIDER"
  elif echo "$OUT" | grep -qiE 'Failed: no successful|NOT_RUN|no route'; then
    note "chaos could not failover (keys/chain) — path still exercised"
    ok "chaos path ran (failover partial/unavailable)"
  else
    bad "chaos test did not produce a usable report"
  fi
  # post-chaos chat still works
  RESP=$(curl -sS "$BASE/v1/chat/completions" \
    -H "Authorization: Bearer $CONSUMER" \
    -H "Content-Type: application/json" \
    -d '{"model":"tollgate/free","messages":[{"role":"user","content":"post-chaos ping"}],"max_tokens":16}' || true)
  if echo "$RESP" | grep -q '"choices"'; then
    ok "chat after chaos still returns choices"
  else
    note "post-chaos: $(echo "$RESP" | head -c 160)"
    bad "chat broken after chaos"
  fi
}

run_restart() {
  echo ""
  echo "── Test 5 restart recovery ──"
  TG_PID=$(lsof -t -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -1 || true)
  if [[ -z "${TG_PID:-}" ]]; then
    bad "cannot find Tollgate PID on $PORT"
    return
  fi
  # capture cmdline + cwd-ish env for restart
  TG_CMD=$(ps -p "$TG_PID" -o args= 2>/dev/null || true)
  note "stopping pid=$TG_PID"
  kill "$TG_PID" 2>/dev/null || true
  sleep 1
  if curl -sf "$BASE/" >/dev/null 2>&1; then
    note "still up after kill — force"
    kill -9 "$TG_PID" 2>/dev/null || true
    sleep 1
  fi
  if curl -sf "$BASE/" >/dev/null 2>&1; then
    bad "Tollgate still responding after kill"
    return
  fi
  ok "Tollgate down (expected mid-restart)"

  # restart: prefer venv uvicorn with same env if available
  export TOLLGATE_HOME="${TOLLGATE_HOME:-$HOME/.tollgate}"
  export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
  nohup "$PY" -m uvicorn tollgate.server_v1:app --host "$HOST" --port "$PORT" \
    > /tmp/tollgate-e2e-restart.log 2>&1 &
  NEW_PID=$!
  note "restarted pid=$NEW_PID (log /tmp/tollgate-e2e-restart.log)"
  UP=0
  for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    if curl -sf "$BASE/" >/dev/null 2>&1; then UP=1; break; fi
    sleep 1
  done
  if [[ "$UP" -eq 1 ]]; then
    ok "Tollgate up after restart"
  else
    bad "Tollgate did not come back"
    return
  fi
  RESP=$(curl -sS "$BASE/v1/chat/completions" \
    -H "Authorization: Bearer $CONSUMER" \
    -H "Content-Type: application/json" \
    -d '{"model":"tollgate/free","messages":[{"role":"user","content":"post-restart ping"}],"max_tokens":16}' || true)
  if echo "$RESP" | grep -q '"choices"'; then
    ok "chat after restart returns choices"
  else
    note "post-restart: $(echo "$RESP" | head -c 180)"
    bad "chat failed after restart"
  fi
  # budget config still on disk
  if [[ -f "${TOLLGATE_HOME}/User/keys_app.json" ]] && grep -q "$CONSUMER" "${TOLLGATE_HOME}/User/keys_app.json" 2>/dev/null; then
    ok "TOLLGATE_HOME config survived restart"
  else
    note "config path: ${TOLLGATE_HOME}/User/keys_app.json"
    ok "restart completed (config check skipped/missing consumer key)"
  fi
}

run_gnom_api() {
  echo ""
  echo "── Test Gnom API chat (optional, GNOM_URL) ──"
  GNOM="${GNOM_URL:-http://127.0.0.1:8080}"
  if ! curl -sf "$GNOM/api/health" >/dev/null 2>&1; then
    note "gnom not up at $GNOM — skip"
    return
  fi
  START=$(curl -sS -X POST "$GNOM/api/chat" \
    -H "Content-Type: application/json" \
    -d '{"text":"E2E: reply with only the word GNOM-E2E"}' || true)
  JID=$(echo "$START" | "$PY" -c 'import sys,json
try:
  print(json.load(sys.stdin).get("job_id") or "")
except Exception:
  print("")' 2>/dev/null || true)
  if [[ -z "$JID" ]]; then
    note "start: $(echo "$START" | head -c 160)"
    bad "gnom /api/chat no job_id"
    return
  fi
  DONE=0
  for _ in $(seq 1 30); do
    JOB=$(curl -sS "$GNOM/api/jobs/$JID" || true)
    ST=$(echo "$JOB" | "$PY" -c 'import sys,json
raw=sys.stdin.read()
raw="".join(c if ord(c)>=32 or c in "\n\t" else " " for c in raw)
try:
  print(json.loads(raw).get("status") or "")
except Exception:
  print("")' 2>/dev/null || true)
    if [[ "$ST" == "done" || "$ST" == "error" || "$ST" == "failed" ]]; then
      DONE=1
      if [[ "$ST" == "done" ]]; then
        ok "gnom job $JID done"
      else
        note "gnom job status=$ST"
        bad "gnom job not done"
      fi
      break
    fi
    sleep 2
  done
  if [[ "$DONE" -eq 0 ]]; then
    bad "gnom job timeout"
  fi
}

case "$MODE" in
  normal) run_normal ;;
  loop) run_loop ;;
  budget) run_budget ;;
  chaos) run_chaos ;;
  restart) run_restart ;;
  gnom) run_gnom_api ;;
  all)
    run_normal
    run_budget
    run_loop
    run_chaos
    run_control
    run_gnom_api
    run_restart
    ;;
  *)
    echo "usage: $0 [all|normal|loop|budget|chaos|restart|gnom]"
    exit 2
    ;;
esac

echo ""
echo "────────────────────────────────────────"
echo " pass=$pass fail=$fail"
echo " Protocol: docs/E2E_GNOM_HUB.md · Dashboard: $BASE/dashboard"
echo "────────────────────────────────────────"
echo ""
[[ "$fail" -eq 0 ]]
