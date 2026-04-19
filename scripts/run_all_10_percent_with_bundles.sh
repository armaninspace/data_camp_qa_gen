#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

BUNDLE_EVERY="${BUNDLE_EVERY:-1}"
BUNDLE_ID_OFFSET="${BUNDLE_ID_OFFSET:-100}"

if [ "${BUNDLE_EVERY}" -le 0 ]; then
  echo "BUNDLE_EVERY must be a positive integer" >&2
  exit 2
fi

case "${BUNDLE_ID_OFFSET}" in
  ''|*[!0-9]*)
    echo "BUNDLE_ID_OFFSET must be digits only" >&2
    exit 2
    ;;
esac

slice_index=0

for start in 0 10 20 30 40 50 60 70 80 90; do
  end=$((start + 10))
  run_id=$(printf 'slice_%03d_%03d' "${start}" "${end}")
  "${SCRIPT_DIR}/run_percent_slice.sh" "${start}" "${end}" "${run_id}"
  slice_index=$((slice_index + 1))

  if [ $((slice_index % BUNDLE_EVERY)) -eq 0 ]; then
    bundle_id=$(printf '%d' $((BUNDLE_ID_OFFSET + slice_index)))
    echo "creating inspection bundle ${bundle_id}" >&2
    "${SCRIPT_DIR}/mk_inspectgion_bundle.sh" "${bundle_id}" "${TMP_ROOT:-/tmp}"
  fi
done
