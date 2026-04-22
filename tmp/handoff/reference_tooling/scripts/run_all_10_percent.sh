#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

for start in 0 10 20 30 40 50 60 70 80 90; do
  end=$((start + 10))
  run_id=$(printf 'slice_%03d_%03d' "${start}" "${end}")
  "${SCRIPT_DIR}/run_percent_slice.sh" "${start}" "${end}" "${run_id}"
done
