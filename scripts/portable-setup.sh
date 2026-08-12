#!/usr/bin/env bash
# One-shot portable / USB layout next to this repo.
# No Docker. Code + optional .venv on stick; data in sibling WS-* folder.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PARENT="$(cd "${ROOT}/.." && pwd)"
# Override: WS_NAME=WS-gnom-hub-v1 ./scripts/portable-setup.sh
WS_NAME="${WS_NAME:-WS-tollgate}"
WS="${PARENT}/${WS_NAME}"

pick_python() {
  local c
  for c in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$c" >/dev/null 2>&1; then
      if "$c" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        echo "$c"
        return 0
      fi
    fi
  done
  return 1
}

echo "Portable setup (no Docker)"
echo "  code: ${ROOT}"
echo "  data: ${WS}"

mkdir -p "${WS}/User"

if [[ ! -f "${WS}/User/Key.txt" ]]; then
  cat > "${WS}/User/Key.txt" <<'EOF'
# Tollgate portable secrets — do not commit
# DEEPSEEK_API_KEY=
# WORKER_API_KEY=
# BRAVE_API_KEY=
# ELEVENLABS_API_KEY=
# ELEVENLABS_MIN_REMAINING=5000
# OPENCODE_API_KEY=
# OPENROUTER_API_KEY=
# NVIDIA_API_KEY=
EOF
  echo "wrote ${WS}/User/Key.txt (skeleton)"
else
  echo "keep ${WS}/User/Key.txt"
fi

if [[ ! -d "${ROOT}/.venv" ]]; then
  if PY="$(pick_python)"; then
    echo "creating ${ROOT}/.venv with $($PY --version 2>&1) …"
    "$PY" -m venv "${ROOT}/.venv"
    "${ROOT}/.venv/bin/pip" install -U pip -q
    "${ROOT}/.venv/bin/pip" install -e "${ROOT}" -q
  else
    echo "ERROR: need Python ≥ 3.10 on PATH (python3.10+)."
    echo "Install via python.org / brew / pyenv — then re-run this script."
    exit 1
  fi
else
  echo "keep ${ROOT}/.venv"
fi

# pin env helper for this shell session instructions
cat <<EOF

Portable ready (native, USB-friendly):
  code:  ${ROOT}
  data:  ${WS}
  keys:  ${WS}/User/Key.txt
  venv:  ${ROOT}/.venv

Run (same stick, no Docker):
  export TOLLGATE_HOME="${WS}"
  # on /Volumes|/media|/mnt auto-detect works without export
  ${ROOT}/scripts/run.sh

With Gnom-Hub on the same volume:
  export GNOM_WS="${WS}"
  export TOLLGATE_HOME="${WS}"
  export TOLLGATE_URL=http://127.0.0.1:8787
  export GNOM_TOLLGATE_LLM=1
  # start Tollgate:  ${ROOT}/scripts/run.sh
  # start Gnom:      (your gnom-hub run; shares Key.txt + ledger)

Smoke paths only:
  ${ROOT}/scripts/portable-smoke.sh

Docs: docs/PORTABLE.md
EOF
