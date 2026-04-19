# Synthetic Cutover Completion Backlog

This backlog covers the remaining work to finish the synthetic-answer cutover.

## Slice 1: Shared Artifact Cutover

Status: in progress

Goal:

- make shared final artifacts reflect the synthetic main path

Tasks:

- publish `synthetic_answers.jsonl`
- publish `synthetic_answer_validation.jsonl`
- publish `synthetic_answer_rewrites.jsonl`
- ensure `answers.jsonl` is the synthetic canonical answer output
- add tests proving shared artifacts match per-course YAML

## Slice 2: Run Summary Cutover

Status: in progress

Goal:

- make `run_summary.yaml` report synthetic counts and decisions

Tasks:

- add synthetic artifact counts to published summary
- add accepted / rewritten / rejected synthetic counts
- keep legacy correctness counts only as derived views from canonical answers
- add tests for summary alignment

## Slice 3: Inspection Bundle Cutover

Status: in progress

Goal:

- make `mk_inspectgion_bundle` consume the synthetic artifact family

Tasks:

- include synthetic shared artifacts in bundle filtering
- include synthetic artifact counts in the manifest
- add tests that the bundle copies synthetic artifacts

## Slice 4: Validator Score Normalization

Status: in progress

Goal:

- normalize validator outputs to one score scale

Tasks:

- detect `1..5` score responses and normalize to `0..1`
- keep `0..1` responses unchanged
- add tests for mixed-scale normalization

## Slice 5: Junk Topic Rejection

Status: in progress

Goal:

- reject obvious garbage topics before question generation

Tasks:

- reject learning-objective fragments like `learn to ...`
- reject preamble labels like `getting started in ...`
- reject wrapper labels like `different types of ...`
- reject bare SQL clause keywords like `where` when emitted as standalone topics
- add focused extraction/vetting tests

## Exit Criteria

This cutover is complete when:

- shared final artifacts and per-course YAML agree
- `run_summary.yaml` reports synthetic counts directly
- inspection bundles contain synthetic shared artifacts
- validator scores are consistently normalized
- junk topics like `where` and `learn to manipulate dataframes` do not survive
