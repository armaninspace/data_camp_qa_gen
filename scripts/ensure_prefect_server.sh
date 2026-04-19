#!/bin/sh
set -eu

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

if python - <<'PY' >/dev/null 2>&1
import os
import urllib.request

api_url = os.environ["PREFECT_API_URL"].rstrip("/")
with urllib.request.urlopen(f"{api_url}/health", timeout=2) as response:
    raise SystemExit(0 if response.status == 200 else 1)
PY
then
  exit 0
fi

echo "starting Prefect server on ${PREFECT_SERVER_API_HOST}:${PREFECT_SERVER_API_PORT}" >&2
prefect server start \
  --host "${PREFECT_SERVER_API_HOST}" \
  --port "${PREFECT_SERVER_API_PORT}" \
  --background \
  --analytics-off >/dev/null

python - <<'PY'
import os
import time
import urllib.request

api_url = os.environ["PREFECT_API_URL"].rstrip("/")

for _ in range(300):
    try:
        with urllib.request.urlopen(f"{api_url}/health", timeout=2) as response:
            if response.status == 200:
                raise SystemExit(0)
    except Exception:
        time.sleep(0.1)

raise SystemExit("Timed out waiting for Prefect server healthcheck")
PY
