#!/bin/sh
set -eu

. "$(dirname -- "$0")/_python_env.sh"

RUN_ID="${1:-first_1_percent}"
INPUT_DIR="${INPUT_DIR:-datacamp_data/classcentral-datacamp-yaml}"
OUTPUT_ROOT="${OUTPUT_ROOT:-data/pipeline_runs}"
FINAL_DIR="${FINAL_DIR:-data/final}"

python -m course_pipeline.cli run \
  --input "${INPUT_DIR}" \
  --output "${OUTPUT_ROOT}/${RUN_ID}" \
  --final-dir "${FINAL_DIR}" \
  --slice-start 0 \
  --slice-end 1 \
  --publish true
