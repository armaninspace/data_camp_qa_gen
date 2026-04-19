#!/bin/sh

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT_DIR="$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)"

export PYTHONPATH="${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
export PREFECT_SERVER_API_HOST="${PREFECT_SERVER_API_HOST:-127.0.0.1}"
export PREFECT_SERVER_API_PORT="${PREFECT_SERVER_API_PORT:-8923}"
export PREFECT_API_URL="${PREFECT_API_URL:-http://${PREFECT_SERVER_API_HOST}:${PREFECT_SERVER_API_PORT}/api}"
export PREFECT_SERVER_EPHEMERAL_ENABLED="${PREFECT_SERVER_EPHEMERAL_ENABLED:-false}"
export PREFECT_SERVER_ALLOW_EPHEMERAL_MODE="${PREFECT_SERVER_ALLOW_EPHEMERAL_MODE:-false}"

if ! python -c "import typer" >/dev/null 2>&1; then
  echo "missing Python dependencies for this repo" >&2
  echo "run: cd ${ROOT_DIR} && python -m pip install -e '.[dev]'" >&2
  echo "or:  cd ${ROOT_DIR} && make bootstrap" >&2
  exit 2
fi

"${SCRIPT_DIR}/ensure_prefect_server.sh"
