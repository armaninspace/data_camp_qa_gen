#!/bin/sh
set -eu

. "$(dirname -- "$0")/_python_env.sh"

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "usage: $0 <slice_start_percent> <slice_end_percent> [run_id]" >&2
  exit 2
fi

SLICE_START="$1"
SLICE_END="$2"
RUN_ID="${3:-slice_${SLICE_START}_${SLICE_END}}"
INPUT_DIR="${INPUT_DIR:-datacamp_data/classcentral-datacamp-yaml}"
OUTPUT_ROOT="${OUTPUT_ROOT:-data/pipeline_runs}"
FINAL_DIR="${FINAL_DIR:-data/final}"

python -m course_pipeline.cli run \
  --input "${INPUT_DIR}" \
  --output "${OUTPUT_ROOT}/${RUN_ID}" \
  --final-dir "${FINAL_DIR}" \
  --slice-start "${SLICE_START}" \
  --slice-end "${SLICE_END}" \
  --publish true
