#!/usr/bin/env bash
# Portable entry: works from repo checkout on disk or USB stick.
# No absolute machine paths. Data: TOLLGATE_HOME / sibling WS-tollgate / ~/.tollgate
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"

# Portable / USB: prefer stick-local data over $HOME
if [[ -z "${TOLLGATE_HOME:-}" && -z "${GNOM_WS:-}" ]]; then
  if [[ -d "${ROOT}/../WS-tollgate" ]]; then
    export TOLLGATE_HOME="$(cd "${ROOT}/../WS-tollgate" && pwd)"
  elif [[ -d "${ROOT}/User" ]]; then
    export TOLLGATE_HOME="${ROOT}"
  elif [[ "${TOLLGATE_PORTABLE:-}" =~ ^(1|true|yes|on|usb)$ ]]; then
    export TOLLGATE_PORTABLE=1
    mkdir -p "${ROOT}/../WS-tollgate/User" 2>/dev/null || mkdir -p "${ROOT}/User"
    if [[ -d "${ROOT}/../WS-tollgate" ]]; then
      export TOLLGATE_HOME="$(cd "${ROOT}/../WS-tollgate" && pwd)"
    else
      export TOLLGATE_HOME="${ROOT}"
    fi
  elif [[ "${ROOT}" == /Volumes/* || "${ROOT}" == /media/* || "${ROOT}" == /run/media/* || "${ROOT}" == /mnt/* ]]; then
    export TOLLGATE_PORTABLE=1
    mkdir -p "${ROOT}/../WS-tollgate/User" 2>/dev/null || mkdir -p "${ROOT}/User"
    if [[ -d "${ROOT}/../WS-tollgate" ]]; then
      export TOLLGATE_HOME="$(cd "${ROOT}/../WS-tollgate" && pwd)"
    else
      export TOLLGATE_HOME="${ROOT}"
    fi
  fi
fi

# Python: venv next to code (USB-friendly) → then PATH
if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PY="${ROOT}/.venv/bin/python"
elif [[ -x "${ROOT}/.venv/bin/python3" ]]; then
  PY="${ROOT}/.venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
else
  PY="$(command -v python)"
fi

PORT="${PORT:-8787}"
HOST="${HOST:-127.0.0.1}"

echo "Tollgate portable"
echo "  ROOT=$ROOT"
echo "  PY=$PY"
echo "  TOLLGATE_HOME=${TOLLGATE_HOME:-"(auto ~/.tollgate or portable)"}"
echo "  → http://${HOST}:${PORT}/docs"

# Prefer module CLI if installed; else uvicorn via PYTHONPATH
if "$PY" -c "import tollgate" 2>/dev/null; then
  exec "$PY" -m uvicorn tollgate.server_v1:app --host "$HOST" --port "$PORT"
fi
exec "$PY" -m uvicorn tollgate.server_v1:app --host "$HOST" --port "$PORT"
