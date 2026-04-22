# Testing And Acceptance

## Testing philosophy

The rewrite should not depend on repeated full corpus runs to discover basic
correctness problems.

Most failures in the current repo were detectable with:

- stage-level unit tests
- small-flow integration tests
- deterministic smoke slices
- publish/bundle validation checks

## Test layers

## 1. Unit tests

Targets:

- normalization
- semantic payload normalization
- family mapping
- provenance propagation
- answer merge rules
- terminal row assembly
- summary metric calculations
- bundle selection filtering

Examples:

- semantic `what_is` becomes canonical entry
- semantic `source_refs` survives generated question creation
- answer and final rows preserve `source_refs`

## 2. Small-flow integration tests

Method:

- run the actual flow entrypoint with fake LLM responses

Examples:

- one course with one entry question
- one course with retained generic but correct Q/A
- one course where teacher answers exist even if semantic answers do not
- one publish and merge scenario

## 3. Publish and merge tests

Method:

- write overlapping slices into the same output/final dirs
- assert only overlapping courses are replaced

## 4. Bundle validation tests

Required:

- filtered bundle consistency
- full bundle consistency
- manifest/log/file parity
- excluded-course leak prevention
- validation artifact emission

## 5. Real-data smoke runs

Minimum smoke procedure:

1. run first 1%
2. inspect full run outputs
3. publish
4. build inspection bundle
5. inspect validation reports

## Mandatory invariants

- every raw course gets a preflight decision
- broken sources do not enter semantic stage
- semantic questions always include `question_family`
- semantic topics/questions always expose `source_refs`
- semantic `what_is` maps to entry semantics
- if upstream refs exist, final surfaced rows preserve provenance
- every generated question reaches answered/rejected/errored
- teacher-answer presence cannot silently disappear before final row assembly
- render fails on terminal-row mismatch
- publish preserves non-overlapping courses
- filtered bundles cannot mix course sets across artifacts

## Minimum regression suite

The rewrite should not be accepted without tests for:

1. `entry_question_count` non-zero when beginner definitions exist
2. semantic `source_refs` surviving into `answers.jsonl`
3. semantic or context refs surviving into `all_rows.jsonl`
4. good Q/A rows surviving into both train and cache outputs
5. same-looking questions remaining distinct across courses
6. teacher-answer presence not yielding silent `missing_answer`
7. shared artifacts and per-course YAML failing on mismatch
8. filtered bundles not mixing course sets
9. summaries distinguishing zero calls from unavailable usage

## Acceptance criteria

Functional:

- one canonical runtime
- no old grounded answer path
- final rows derived from the canonical answer path

Artifact:

- `answers.jsonl`, `all_rows.jsonl`, `train_rows.jsonl`, `cache_rows.jsonl`,
  and per-course YAML agree on answer presence and course scope

Provenance:

- surfaced answered rows preserve `source_refs`

Observability:

- run summary reports honest LLM usage state and cost state

Bundle:

- every bundle artifact agrees with manifest and validation report

Operational:

- first 1% smoke run passes
- at least one real incremental publish sequence passes
- at least one filtered and one full bundle validate successfully
