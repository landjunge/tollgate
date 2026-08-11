#!/usr/bin/env bash
# Fail if docs/configs still teach the old gnom-hub keys world.
# Allowlisted lines use the marker:  # legacy-ok  OR  <!-- legacy-ok -->
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FAIL=0
scan() {
  local label="$1"
  local pattern="$2"
  local files="$3"
  # shellcheck disable=SC2086
  local hits
  hits=$(grep -nE "$pattern" $files 2>/dev/null | grep -vE 'legacy-ok|No `gnom_hub|Not.*Gnom hub|:8080.*/api/mcp' || true)
  if [[ -n "$hits" ]]; then
    echo "FAIL [$label]:"
    echo "$hits"
    FAIL=1
  else
    echo "ok   [$label]"
  fi
}

echo "=== Tollgate docs drift check ==="
scan "old package imports in docs" \
  'from gnom_hub\.keys|import gnom_hub\.keys|python -m gnom_hub\.keys|gnom_hub\.keys\.(mcp|service)' \
  "docs README.md"

scan "old distill path" \
  'src/gnom_hub/keys/distill|gnom_hub/keys/distill' \
  "docs README.md configs"

scan "hub keys API path" \
  '/api/keys/|/api/mcp/keys' \
  "docs README.md"

scan "dead hub port as primary (8787 is tollgate)" \
  '127\.0\.0\.1:8080|localhost:8080' \
  "docs README.md configs"

scan "absolute home paths" \
  '/Users/landjunge|/Users/[a-zA-Z0-9_-]+/(gnom|tollgate)' \
  "docs README.md configs scripts"

if [[ "$FAIL" -ne 0 ]]; then
  echo ""
  echo "Docs/code drift detected. Fix paths/ports or mark intentional lines with 'legacy-ok'."
  exit 1
fi
echo "All drift checks passed."
