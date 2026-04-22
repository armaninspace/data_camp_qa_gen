# Reference Material Map

Use this file as the bridge between the rewrite docs and the copied reference
material in `tmp/handoff`.

## If you need raw examples

Start with:

- `reference_input/raw_courses/`

These show the shape and messiness of real scraped course files.

## If you need to understand recent failures

Start with:

- `docs/01_failures_and_lessons.md`
- `docs/current_bundle_qa_report.md`
- `docs/latest_pipeline_run_feedback.md`
- `docs/interrogation_answers.md`

## If you need to see a real run directory

Start with:

- `reference_runs/first_1_percent/`

Inspect:

- `run_summary.yaml`
- `answers.jsonl`
- `all_rows.jsonl`
- `course_yaml/`
- `logs/`

## If you need current operator commands

Start with:

- `reference_tooling/scripts/`
- `reference_tooling/Makefile`
- `docs/04_ops_and_tooling.md`

## If you need current implementation boundaries

Start with:

- `reference_tooling/src/course_pipeline/schemas.py`
- `reference_tooling/src/course_pipeline/flows/course_question_pipeline.py`
- `reference_tooling/src/course_pipeline/tasks/`

## If you need behavioral examples

Start with:

- `reference_tooling/tests/test_flow_synthetic_migration.py`
- `reference_tooling/tests/test_build_ledger.py`
- `reference_tooling/tests/test_artifact_upsert.py`
- `reference_tooling/tests/test_inspectgion_bundle.py`
