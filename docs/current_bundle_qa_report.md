# Current Bundle QA Report

## Scope

This report separates three layers that were previously conflated:

- core run health
- bundle publication integrity
- published LLM observability availability

It reflects the code and test state after the bundle-selection and validation
fixes, plus the current local workspace state on 2026-04-21.

## Core Run

The current code path preserves the new product contract:

- `course_context_frames.jsonl`
- `question_context_frames.jsonl`
- `train_rows.jsonl`
- `cache_rows.jsonl`
- `answers.jsonl`
- `all_rows.jsonl`

Recent fixes kept the retained-teacher-answer path as the canonical answer
source and added hard consistency checks between shared artifacts and per-course
YAML.

Status: `pass` at the code and test level.

Evidence:

- `tests/test_flow_synthetic_migration.py`
- `tests/test_build_ledger.py`
- `tests/test_artifact_upsert.py`

## Bundle Integrity

The bundle exporter now builds one canonical selection object first and uses it
for every exported artifact. It writes both machine-readable and human-readable
validation output:

- `bundle_validation.json`
- `bundle_validation.md`

The bundle log is now selection-derived instead of descriptive-only.

Status: `pass` at the code and regression-test level.

Evidence:

- `tests/test_inspectgion_bundle.py` asserts:
  - filtered bundles contain only the selected courses
  - `answers.jsonl` and `all_rows.jsonl` match the selected course set
  - `pipeline_run_manifest.yaml`, `bundle_validation.json`, and
    `inspectgion_bundle.log` agree on the selection
  - `bundle_validation.md` is emitted

Interpretation:

- the publication bug was a bundle-layer selection drift problem
- the implemented fix is a canonical-selection-and-validate design
- this is the correct repair; it does not require rewriting the core pipeline

## LLM Observability

Published run summaries now distinguish between:

- `ok`
- `partial`
- `no_calls`
- `usage_reporting_unavailable`

This matters because a historical published tree can lack
`logs/llm_calls.jsonl`, and that should not be reported as if the pipeline made
zero model calls.

Status: `pass` for summary semantics and future publishes.

Evidence:

- `tests/test_artifact_upsert.py`
- `tests/test_publish_and_logging.py`
- `src/course_pipeline/tasks/render.py`

Current local published-tree state:

- `rebuild_run_summary(data/final)` currently reports:
  - `llm_call_count: 0`
  - `llm_cost_reporting_status: usage_reporting_unavailable`

Interpretation:

- instrumentation semantics are now honest
- the currently checked-out `data/final` tree does not contain published LLM
  usage logs to aggregate

## Local Blocker

This workspace currently cannot regenerate the latest filtered bundle from
`data/final` because the local worktree has unrelated deletions under
`data/final/`, including the course bundles needed as the source tree.

Observed local failure:

- `mk_inspectgion_bundle 14 --final-dir data/final --tmp-root /tmp`
- result: failure because `data/final/course_yaml/*.yaml` is absent in the
  current worktree

This is a workspace-state blocker, not evidence that the bundle exporter is
still selecting rows inconsistently.

## Conclusion

Current assessment:

- core pipeline contract: fixed and preserved
- filtered bundle integrity design: fixed in code and covered by regression
  tests
- published LLM observability semantics: fixed in code and covered by tests
- historical/local `data/final` regeneration: blocked by missing source files in
  the current worktree

## Next Action

To re-run end-to-end QA against the latest real published run, restore or
recreate a valid `data/final` source tree first, then regenerate the filtered
bundle and compare:

- `pipeline_run_manifest.yaml`
- `inspectgion_bundle.log`
- `bundle_validation.json`
- `bundle_validation.md`
- exported flat artifact course sets and counts
