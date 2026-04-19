#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT_DIR="$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)"

export PYTHONPATH="${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
export PREFECT_SERVER_API_HOST="${PREFECT_SERVER_API_HOST:-127.0.0.1}"
export PREFECT_SERVER_API_PORT="${PREFECT_SERVER_API_PORT:-8923}"
export PREFECT_API_URL="${PREFECT_API_URL:-http://${PREFECT_SERVER_API_HOST}:${PREFECT_SERVER_API_PORT}/api}"

prefect server status "$@"
