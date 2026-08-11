#!/usr/bin/env bash
# Killer demo: Protect (tool loop block) + optional Prove (chaos).
# Story: "My AI agent must never go out of control."
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export TOLLGATE_HOME="${TOLLGATE_HOME:-${GNOM_WS:-$HOME/.tollgate}}"
export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-8787}"
BASE="http://${HOST}:${PORT}"
PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY=python3
CONSUMER="${DEMO_CONSUMER:-support-agent}"
CHAOS_PROVIDER="${DEMO_CHAOS_PROVIDER:-opencode_zen}"
SKIP_CHAOS="${SKIP_CHAOS:-0}"

cd "$ROOT"
mkdir -p "$TOLLGATE_HOME/User"

echo "════════════════════════════════════════════════════════"
echo " TOLLGATE DEMO — agent safety layer"
echo " “My AI agent must never go out of control.”"
echo " home=$TOLLGATE_HOME  base=$BASE  consumer=$CONSUMER"
echo "════════════════════════════════════════════════════════"
echo ""

if ! curl -sf "$BASE/v1/health" >/dev/null 2>&1; then
  echo "→ Starting Tollgate on $BASE …"
  nohup "$PY" -m uvicorn tollgate.server_v1:app --host "$HOST" --port "$PORT" \
    > /tmp/tollgate-demo.log 2>&1 &
  echo $! > /tmp/tollgate-demo.pid
  for _ in $(seq 1 20); do
    curl -sf "$BASE/v1/health" >/dev/null 2>&1 && break
    sleep 0.3
  done
fi

if ! curl -sf "$BASE/v1/health" >/dev/null 2>&1; then
  echo "FAIL: server not up at $BASE (log: /tmp/tollgate-demo.log)"
  exit 1
fi

echo "→ Protect lane: $CONSUMER (\$2/day, 20 tool calls, free_llm+chat)"
"$PY" -m tollgate.cli consumer-budget "$CONSUMER" \
  --max-usd-day 2 \
  --max-usd-request 0.5 \
  --max-requests-minute 50 \
  --max-tool-calls 20 \
  --allow-intent free_llm --allow-intent llm \
  --allow-op chat >/dev/null

echo ""
echo "────────────────────────────────────────────────────────"
echo " AHA #1 — PROTECT: agent tool-loop → BLOCKED"
echo "────────────────────────────────────────────────────────"
echo "Simulating tool_calls_est=99 (limit 20)…"
echo ""

RESP=$(curl -sS "$BASE/v1/invoke" \
  -H 'Content-Type: application/json' \
  -H "X-Consumer-Key: $CONSUMER" \
  -d "{
    \"provider\": \"${CHAOS_PROVIDER}\",
    \"op\": \"chat\",
    \"tool_calls_est\": 99,
    \"tokens_est\": 100,
    \"arguments\": {\"message\": \"demo loop\"},
    \"agent_id\": \"${CONSUMER}\",
    \"request_class\": \"interactive\"
  }")

echo "$RESP" | "$PY" -c '
import json,sys
d=json.load(sys.stdin)
b=d.get("blocked") or {}
if b.get("message"):
    print(b["message"])
else:
    print("ok=", d.get("ok"), "error=", d.get("error"))
    if d.get("protection"):
        print("protection=", d.get("protection"))
print()
print("JSON keys:", ", ".join(sorted(d.keys())[:12]), "…")
' 2>/dev/null || echo "$RESP"

echo ""
echo "Audit (who/why):"
"$PY" -m tollgate.cli audit --event admit_deny --consumer "$CONSUMER" --limit 3 2>/dev/null \
  | "$PY" -c 'import json,sys
try:
  d=json.load(sys.stdin)
  for e in (d.get("events") or [])[:3]:
    print(" -", e.get("consumer"), e.get("error","")[:80])
except Exception:
  pass
' || true

if [[ "$SKIP_CHAOS" != "1" ]]; then
  echo ""
  echo "────────────────────────────────────────────────────────"
  echo " AHA #2 — PROVE: primary outage → survive?"
  echo "────────────────────────────────────────────────────────"
  echo "Chaos test provider=$CHAOS_PROVIDER (router-only probes, low cost)…"
  echo ""
  "$PY" -m tollgate.cli chaos test "$CHAOS_PROVIDER" --requests 8 --intent free_llm 2>/dev/null \
    | "$PY" -c '
import json,sys
try:
  d=json.load(sys.stdin)
except Exception as e:
  print("chaos output not JSON:", e); sys.exit(0)
print("Provider:   ", d.get("chaos_provider"))
print("Requests:   ", d.get("requests_tested"))
print("Successful: ", d.get("successful"))
print("Failed:     ", d.get("failed"))
print("Failover %: ", d.get("automatic_failover_pct"))
print("Recovery ms:", d.get("recovery_time_ms_best"))
print("Survived:   ", d.get("survived"))
print()
print(d.get("message") or "")
if d.get("survived"):
  print()
  print("✓ Your agent survived.")
' || echo "(chaos test skipped or failed — check providers enabled)"
fi

echo ""
echo "────────────────────────────────────────────────────────"
echo " Status"
echo "────────────────────────────────────────────────────────"
"$PY" -m tollgate.cli status 2>/dev/null || true

echo ""
echo "════════════════════════════════════════════════════════"
echo " Demo complete"
echo "  Dashboard: $BASE/dashboard"
echo "  Docs:      docs/DEMO.md"
echo "  Story:     safety layer between agents and the internet"
echo "  Skip DR:   SKIP_CHAOS=1 $0"
echo "════════════════════════════════════════════════════════"
