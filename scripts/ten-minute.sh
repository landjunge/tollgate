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
echo "────────────────────────────────────────────────────────"
echo " Checklist (stranger test)"
echo "────────────────────────────────────────────────────────"
"$PY" - <<'PY' 2>/dev/null || true
from tollgate.certificate import build_certificate
c = build_certificate()
ids = {x["id"]: x for x in (c.get("checks") or [])}
def row(cid, label):
    ch = ids.get(cid) or {}
    st = ch.get("status") or "?"
    mark = {"PASS": "✓", "FAIL": "✗", "NOT_RUN": "·", "READY": "·"}.get(st, "·")
    print(f"  {mark} {label:<28} {st}")
print(f"  Overall: {c.get('overall')}")
row("budget_protection", "Know what this is for")
row("agent_loop_protection", "Runaway can be hard-stopped")
row("provider_failover", "Failover can be proven")
if c.get("prove_pending") or (ids.get("provider_failover") or {}).get("status") == "NOT_RUN":
    print("  · Prove pending is OK if Protect passed — finish chaos when keys ready")
if (ids.get("provider_failover") or {}).get("status") == "FAIL":
    print("  · DR failed — free_llm needs a second keyed provider (see chaos next_step)")
print(f"  Resilience: {c.get('resilience_score')}/100")
PY

echo ""
echo "  Dashboard: http://${HOST}:${PORT}/dashboard"
echo "  If anything above was confusing → that's the product bug."
echo "  Docs for strangers: docs/TEN_MINUTE.md"
echo ""
