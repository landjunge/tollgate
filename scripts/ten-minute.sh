#!/usr/bin/env bash
# Cold-customer 10-minute path: Protect → Prove → certificate → dashboard.
# Conversion metric: install → first protected request (loop block felt).
# No feature tour. No architecture. One result.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export TOLLGATE_HOME="${TOLLGATE_HOME:-${GNOM_WS:-$HOME/.tollgate}}"
export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-8787}"
BASE="http://${HOST}:${PORT}"
DASH="${BASE}/dashboard"
OPEN_DASH="${OPEN_DASHBOARD:-1}"

cd "$ROOT"
mkdir -p "$TOLLGATE_HOME/User"

PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY=python3

echo ""
echo "  TOLLGATE — 10-minute test"
echo "  Protect · Route · Prove"
echo "  Connect your agent. Tollgate protects it automatically."
echo ""
echo "  You should leave knowing:"
echo "    1) what this is for"
echo "    2) that a runaway agent can be hard-stopped"
echo "    3) that failover can be proven (or clear next step)"
echo ""

# ── Protect + Prove (existing demo) ───────────────────────────────────
SKIP_CHAOS="${SKIP_CHAOS:-0}" bash "$ROOT/scripts/demo-agent-safety.sh"

echo ""
echo "────────────────────────────────────────────────────────"
echo " RESULT — scorecard"
echo "────────────────────────────────────────────────────────"
echo ""

"$PY" -m tollgate.cli certificate 2>/dev/null || true

echo ""
echo "────────────────────────────────────────────────────────"
echo " What Tollgate prevented (this session)"
echo "────────────────────────────────────────────────────────"
"$PY" - <<'PY' 2>/dev/null || true
from tollgate.control_plane import control_snapshot
s = control_snapshot()
ps = s.get("protection_summary") or {}
sum_ = s.get("summary") or {}
print(f"  Loop stops:         {ps.get('loop_stops', sum_.get('agent_protection_blocks', 0))}")
print(f"  Requests blocked:   {ps.get('requests_blocked', sum_.get('admit_denies', 0))}")
print(f"  Agents protected:   {ps.get('agents_protected', sum_.get('consumers_protected', 0))}")
print(f"  Failovers seen:     {ps.get('failovers_seen', 0)}")
print(f"  Spent today:        ${float(sum_.get('usd') or 0):.4f}")
print()
print("  " + (ps.get("tagline") or "Connect your agent. Tollgate protects it automatically."))
PY

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
row("agent_loop_protection", "Runaway hard-stopped")
row("provider_failover", "Failover proven")
if c.get("prove_pending") or (ids.get("provider_failover") or {}).get("status") == "NOT_RUN":
    print("  · Prove pending is OK if Protect passed — finish chaos when keys ready")
if (ids.get("provider_failover") or {}).get("status") == "FAIL":
    print("  · DR failed — free_llm needs a second keyed provider")
print(f"  Resilience: {c.get('resilience_score')}/100")
PY

echo ""
echo "────────────────────────────────────────────────────────"
echo " NEXT — Control Room (first success)"
echo "────────────────────────────────────────────────────────"
echo "  Dashboard:  ${DASH}"
echo "  1) Protect my first agent  (or re-run loop test)"
echo "  2) Prove my setup          (when ≥2 providers + keys)"
echo "  3) See protection in action"
echo ""
echo "  Server should still be up (demo started it if needed)."
echo "  Leave it running:  tollgate serve"
echo "  If anything above was confusing → that's the product bug."
echo "  Docs: docs/TEN_MINUTE.md · docs/PRODUCT_NORTH_STAR.md"
echo ""

if [[ "$OPEN_DASH" == "1" ]]; then
  if command -v open >/dev/null 2>&1; then
    open "$DASH" 2>/dev/null || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$DASH" 2>/dev/null || true
  fi
fi
