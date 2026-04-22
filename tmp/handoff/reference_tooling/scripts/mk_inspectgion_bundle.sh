#!/bin/sh
set -eu

. "$(dirname -- "$0")/_python_env.sh"

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT_DIR="$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)"

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "usage: $0 <bundle_id> [tmp_root]" >&2
  exit 2
fi

BUNDLE_ID="$1"
TMP_ROOT="${2:-${ROOT_DIR}/tmp}"
FINAL_DIR="${FINAL_DIR:-data/final}"

python -m course_pipeline.cli mk_inspectgion_bundle \
  "${BUNDLE_ID}" \
  --final-dir "${FINAL_DIR}" \
  --tmp-root "${TMP_ROOT}"
