#!/usr/bin/env bash
# Ampel: docs migration status gnom-hub → tollgate
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

green=0
yellow=0
red=0

check_file() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  local bad=0
  local notes=()
  if grep -qE 'src/gnom_hub/keys|from gnom_hub\.keys|python -m gnom_hub' "$f" 2>/dev/null; then
    bad=$((bad + 1))
    notes+=("old package path")
  fi
  if grep -qE '127\.0\.0\.1:8080|/api/keys/' "$f" 2>/dev/null; then
    bad=$((bad + 1))
    notes+=("old hub API/port")
  fi
  if grep -qE 'src/gnom_hub/keys/distill' "$f" 2>/dev/null; then
    bad=$((bad + 1))
    notes+=("old distill path")
  fi
  local good=0
  if grep -qE 'tollgate|/v1/|8787|src/tollgate' "$f" 2>/dev/null; then
    good=1
  fi

  local status
  if [[ "$bad" -eq 0 && "$good" -eq 1 ]]; then
    status="GREEN "
    green=$((green + 1))
  elif [[ "$bad" -eq 0 ]]; then
    status="YELLOW"
    yellow=$((yellow + 1))
  else
    status="RED   "
    red=$((red + 1))
  fi
  local note=""
  if [[ ${#notes[@]} -gt 0 ]]; then
    note=" — ${notes[*]}"
  fi
  printf '%s  %s%s\n' "$status" "$f" "$note"
}

echo "=== Migration status (docs) ==="
while IFS= read -r f; do
  check_file "$f"
done < <(find docs -name '*.md' 2>/dev/null; printf '%s\n' README.md configs/*.json 2>/dev/null || true)

echo ""
echo "Summary: green=$green yellow=$yellow red=$red"
if [[ "$red" -gt 0 ]]; then
  echo "Not migration-clean yet."
  exit 1
fi
echo "Migration docs look clean (or only soft yellow)."
