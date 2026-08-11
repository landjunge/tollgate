#!/usr/bin/env bash
# One-shot portable / USB layout next to this repo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PARENT="$(cd "${ROOT}/.." && pwd)"
WS="${PARENT}/WS-tollgate"

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
  if command -v python3 >/dev/null 2>&1; then
    echo "creating ${ROOT}/.venv …"
    python3 -m venv "${ROOT}/.venv"
    "${ROOT}/.venv/bin/pip" install -U pip -q
    "${ROOT}/.venv/bin/pip" install -e "${ROOT}" -q
  else
    echo "python3 not found — skip venv"
  fi
fi

cat <<EOF

Portable ready:
  code:  ${ROOT}
  data:  ${WS}
  keys:  ${WS}/User/Key.txt

Run:
  export TOLLGATE_HOME="${WS}"
  # or on USB mounts: auto-detect without export
  ${ROOT}/scripts/run.sh
EOF
