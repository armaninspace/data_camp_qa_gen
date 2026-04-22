# Operations And Tooling

## Objective

The rewrite is not complete without the operator tooling required to run,
inspect, publish, and validate it.

## Required command surfaces

## 1. Main run command

Required CLI shape:

```sh
python -m course_pipeline.cli run \
  --input <input_dir> \
  --output <run_dir> \
  --final-dir <final_dir> \
  --slice-start <start_percent> \
  --slice-end <end_percent> \
  --publish true|false
```

Required behavior:

- deterministic lexicographic slice ordering
- transient run outputs under `data/pipeline_runs/<run_id>`
- optional publish into `data/final`

## 2. Smoke-run utility

Required script:

- `scripts/run_first_1_percent.sh`

Purpose:

- fast real-data smoke test

## 3. Arbitrary slice utility

Required script:

- `scripts/run_percent_slice.sh <slice_start> <slice_end> [run_id]`

## 4. Sweep utilities

Required scripts:

- `scripts/run_all_5_percent.sh`
- `scripts/run_all_10_percent.sh`
- optional bundle-checkpoint variants

## 5. Inspection bundle utility

Required CLI/script:

- `python -m course_pipeline.cli mk_inspectgion_bundle <bundle_id>`
- `scripts/mk_inspectgion_bundle.sh`

Required options:

- `--export-mode filtered|full`
- `--final-dir`
- `--tmp-root`

Required outputs:

- `pipeline_run_manifest.yaml`
- `bundle_validation.json`
- `bundle_validation.md`
- `run_summary.yaml`
- `source_run_summary.yaml`

## 6. Environment bootstrap

Required:

- reproducible package install
- test dependencies
- LLM client configuration
- local run prerequisites

The current repo uses `pyproject.toml` plus shell helpers; the rewrite may keep
or replace that, but the new team must ship an equally explicit bootstrap path.

## 7. Local orchestration

Current repo uses Prefect local server helpers.

The rewrite team may:

- keep Prefect and formalize it
- or replace it with something simpler

Either is acceptable as long as local execution, failure visibility, and slice
determinism stay explicit.

## Utility software expected in the rewrite

Core:

- run one slice
- run first 1%
- run deterministic sweep
- publish merged outputs
- build inspection bundle
- rebuild run summary from artifacts
- validate bundle

Debug:

- inspect one course end to end
- inspect one question id across semantic rows, context frames, answers, and
  final rows
- diff artifact counts before and after publish

Reporting:

- run summary rebuild
- bundle validation render
- LLM usage/cost rollup
- artifact consistency check

## Required runbook procedures

Smoke run:

1. install environment
2. run first 1%
3. inspect `run_summary.yaml`
4. inspect `answers.jsonl` and `all_rows.jsonl`
5. publish
6. build inspection bundle
7. inspect validation reports

Incremental rollout:

1. run deterministic slices in ascending order
2. inspect `data/final/run_summary.yaml` after each publish
3. create periodic bundle checkpoints
4. stop on first invalid publish or bundle validation failure

Failure triage must be able to answer:

- did preflight exclude the source?
- did semantic stage fail?
- did policy tagging fail?
- did answer generation fail?
- did terminal row assembly fail?
- did render consistency fail?
- did publish fail?
- did bundle validation fail?

## Bundle interpretation rules

1. full-run artifacts are authoritative
2. published `data/final` is merged run truth
3. filtered bundle is only a projection
4. filtered bundle must never be mistaken for full-run truth
