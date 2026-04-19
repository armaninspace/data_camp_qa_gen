
# Architecture Notes

## Orchestration

Use Prefect.

Main flow:
- `course_question_pipeline_flow`

Tasks:
1. `load_course_records`
2. `normalize_course`
3. `extract_atomic_topics`
4. `canonicalize_topics`
5. `generate_question_candidates`
6. `repair_or_reject_questions`
7. `answer_questions`
8. `build_ledger_rows`
9. `render_per_course_yaml_bundle`
10. `render_run_summary`

Required post-flow step:
- `publish_final_outputs`

Post-publish job:
- `mk_inspectgion_bundle`

## Storage model

Start file-first.

Run directory:
```text
data/pipeline_runs/<run_id>/
  normalized_courses.jsonl
  topics.jsonl
  canonical_topics.jsonl
  question_candidates.jsonl
  question_repairs.jsonl
  answers.jsonl
  all_rows.jsonl
  run_summary.yaml
  logs/
    pipeline.log
    llm_calls.jsonl
    stage_metrics.jsonl
    publish.log
    inspectgion_bundle.log
  course_yaml/
    <course_id>.yaml
```

Published directory:
```text
data/final/
  normalized_courses.jsonl
  topics.jsonl
  canonical_topics.jsonl
  question_candidates.jsonl
  question_repairs.jsonl
  answers.jsonl
  all_rows.jsonl
  run_summary.yaml
  course_yaml/
    <course_id>.yaml
```

Inspection bundle directory:
```text
/tmp/inspectgion_bundl_<bundle_id>/
  normalized_courses.jsonl
  topics.jsonl
  canonical_topics.jsonl
  question_candidates.jsonl
  question_repairs.jsonl
  answers.jsonl
  all_rows.jsonl
  run_summary.yaml
  pipeline_run_manifest.yaml
  course_yaml/
    <course_id>.yaml
```

## Why file-first

- easy to diff
- easy to inspect
- easy to hand to humans
- lower operational cost early on

Optional later:
- Postgres
- pgvector

## Incremental writes

The file-first storage model must support course-level upserts.

For shared JSONL artifacts:
- identify the set of `course_id`s in the current slice
- rewrite each artifact file so rows for those `course_id`s are removed
- append the fresh rows for those same `course_id`s
- preserve rows for all other courses

For per-course YAML:
- rewrite only `course_yaml/<course_id>.yaml` files for affected courses

For summaries:
- compute run summary values from the merged artifact state after upsert

This allows overlapping slice runs without duplicating rows in JSONL outputs.

Slice selection:
- resolve percent-based or range-based slices against a stable deterministic
  ordering of input files
- default ordering is lexicographic by input file path
- normalize input paths relative to the selected input root before ordering
- compute overlap from the expanded selected `course_id` set

## Publish step

After a full successful pipeline run, copy the merged outputs into `data/final`.

Rules:
- `data/pipeline_runs/<run_id>/` remains the transient per-run workspace
- `data/final/` is the stable checked-in output location
- publish only after the run has completed successfully
- use the same `course_id`-based upsert semantics in `data/final`
- rewrite only affected `course_yaml/<course_id>.yaml` files in `data/final`
- rebuild `data/final/run_summary.yaml` from the published merged state

Publish success criteria:
- every selected input course must have a rendered per-course bundle
- shared JSONL artifacts for the run must be present and internally consistent
- terminal question-row states may include `answered`, `rejected`, and
  `errored`
- if the run aborts before rendering completes, do not publish
- log publish-block reasons explicitly

This keeps debug artifacts separate from versioned deliverables.

## Logging

Treat logging as an operational artifact, not an afterthought.

Per-run logging rules:
- create a dedicated `logs/` directory under each run directory
- keep log files separate by run
- use structured records where possible, especially for LLM and stage metrics
- make logs human-readable enough for local debugging and machine-readable
  enough for later analysis

Required logging coverage:
- pipeline lifecycle events
- per-stage start, completion, duration, and row counts
- warnings and exceptions with enough context to diagnose failures
- upsert decisions for overlapping `course_id`s
- publish actions into `data/final`
- inspection-bundle assembly actions

LLM logging requirements:
- record one structured log event per LLM call
- include stage name, prompt family, configured model, requested model, and
  actual model used
- include provider request id or response id when available
- include token usage, latency, and retry count when available
- never log secrets

Stable structured log schemas:

`logs/llm_calls.jsonl`
- `timestamp`
- `run_id`
- `course_id`
- `stage`
- `prompt_family`
- `configured_model`
- `requested_model`
- `actual_model`
- `actual_model_source`
- `provider_request_id`
- `latency_ms`
- `tokens_in`
- `tokens_out`
- `retry_count`
- `status`

`logs/stage_metrics.jsonl`
- `timestamp`
- `run_id`
- `course_id`
- `stage`
- `event`
- `duration_ms`
- `input_row_count`
- `output_row_count`
- `warning_count`
- `error_count`

Actual model semantics:
- `actual_model` should record the most specific provider-confirmed model
  identifier available from the response
- if the provider returns both an alias and a versioned snapshot, prefer the
  versioned snapshot in `actual_model`
- record the provenance in `actual_model_source`, for example:
  - `response.model`
  - `response.metadata.model`
  - `fallback_requested_model`

## Inspection bundle step

The inspection bundle job reads from `data/final` and writes a stable
four-course subset bundle under `/tmp/inspectgion_bundl_<bundle_id>`.

Rules:
- accept a digits-only bundle id
- filter all shared final JSONL artifacts down to the selected course ids
- copy only the selected `course_yaml/<course_id>.yaml` files
- write `pipeline_run_manifest.yaml` containing:
  - selection metadata
  - artifact counts per stage
  - per-course YAML file counts
  - published-run performance data when available
  - bundle build timing data
  - bundle log ownership metadata
- fail fast if any required selected course output is missing from `data/final`
- allow empty filtered artifact files when they accurately reflect the selected
  courses' published state

Inspection-bundle log ownership:
- the bundle job does not write into a prior pipeline run's `logs/` directory
- the bundle job should write its own log file inside the bundle directory or
  another bundle-scoped location
- `logs/inspectgion_bundle.log` under a run directory is optional and applies
  only when bundle creation is initiated as part of that run context

The fixed default selection should include:
- 2 R courses
- 1 SQL course
- 1 Python course

This bundle is for rapid inspection and regression review, not for git.

## Prompt architecture

Prompt A:
- extract atomic topics

Prompt B:
- expand questions from pattern bank

Prompt C:
- repair or reject

Prompt D:
- answer and rate correctness

## Suggested model use

`gpt-5.4`
- topic extraction
- repair/reject
- answer correctness

`gpt-5.4-mini`
- question expansion
- cheap large-batch generation

## Debugging philosophy

The easiest failure diagnosis should be:

- topic missing
- question generated badly
- question rejected
- answer unsupported

If the system makes that hard, simplify the design.

## Test strategy

Prefer a heavy unit-test baseline.

Test layers:
- unit tests for stage functions and file-merging utilities
- regression tests using a small fixed set of real scraped course fixtures
- command-level tests for publish and inspection-bundle workflows when the
  runtime wiring is in place

Critical test targets:
- normalization against the Class Central DataCamp YAML shape
- course-level upsert semantics for overlapping slice runs
- merged-summary rebuilding after upsert and publish
- inspection-bundle manifest counts and selected-course filtering
