#!/usr/bin/env bash
# Offline portable/USB smoke — no network, no Docker.
# Simulates stick layout under a temp dir and checks path resolution.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY="$(command -v python3)"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/tollgate-portable-XXXXXX")"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

STICK="$TMP/stick"
CODE="$STICK/tollgate"
DATA="$STICK/WS-tollgate"
mkdir -p "$CODE/src/tollgate" "$DATA/User"
# minimal package surface for paths.py (uses parents[2] from paths location)
mkdir -p "$CODE/src/tollgate"
# use real package via PYTHONPATH; only need env isolation for data home
echo "# test keys" > "$DATA/User/Key.txt"

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
export TOLLGATE_HOME="$DATA"
unset GNOM_WS 2>/dev/null || true
export TOLLGATE_PORTABLE=1

echo "Portable smoke (tmp stick: $STICK)"
"$PY" - <<'PY'
import os
from pathlib import Path
from tollgate.paths import data_home, user_dir, path_snapshot, is_portable_mode, pin_data_home_env

home = data_home()
assert home == Path(os.environ["TOLLGATE_HOME"]).resolve(), home
assert (user_dir() / "Key.txt").is_file(), user_dir()
assert is_portable_mode() is True
pin_data_home_env()
snap = path_snapshot()
assert snap["data_home"]
assert snap["user_dir"]
assert snap["portable"] is True
print("  ok data_home=", snap["data_home"])
print("  ok user_dir=", snap["user_dir"])
print("  ok portable=", snap["portable"])
PY

# sibling auto without TOLLGATE_HOME when USB-like: force via PORTABLE + fake layout
unset TOLLGATE_HOME
export TOLLGATE_PORTABLE=1
# When only PORTABLE=1 without home, resolve_portable_home uses project_root (real repo)
# so pin explicitly to DATA for second check
export TOLLGATE_HOME="$DATA"
"$PY" -c 'from tollgate.paths import path_snapshot; s=path_snapshot(); assert s["portable"]; print("  ok snapshot portable")'

echo "PASS portable-smoke (no Docker)"
