#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

for start in 0 5 10 15 20 25 30 35 40 45 50 55 60 65 70 75 80 85 90 95; do
  end=$((start + 5))
  run_id=$(printf 'slice_%03d_%03d' "${start}" "${end}")
  "${SCRIPT_DIR}/run_percent_slice.sh" "${start}" "${end}" "${run_id}"
done
