#!/usr/bin/env bash
# Cold-customer 10-minute path: Protect → Prove → certificate scorecard.
# No feature tour. No architecture. One result.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export TOLLGATE_HOME="${TOLLGATE_HOME:-${GNOM_WS:-$HOME/.tollgate}}"
export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-8787}"

cd "$ROOT"
mkdir -p "$TOLLGATE_HOME/User"

echo ""
echo "  TOLLGATE — 10-minute test"
echo "  Protect your AI agents from cost explosions and provider outages."
echo ""
echo "  You should leave knowing:"
echo "    1) what this is for"
echo "    2) that a runaway agent can be hard-stopped"
echo "    3) that failover can be proven"
echo ""

# ── Protect + Prove (existing demo) ───────────────────────────────────
SKIP_CHAOS="${SKIP_CHAOS:-0}" bash "$ROOT/scripts/demo-agent-safety.sh"

echo ""
echo "────────────────────────────────────────────────────────"
echo " RESULT — AI reliability scorecard"
echo "────────────────────────────────────────────────────────"
echo ""

PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY=python3
"$PY" -m tollgate.cli certificate 2>/dev/null || true

echo ""
echo "  Dashboard: http://${HOST}:${PORT}/dashboard"
echo "  If anything above was confusing → that's the product bug."
echo "  Docs for strangers: docs/TEN_MINUTE.md"
echo ""
