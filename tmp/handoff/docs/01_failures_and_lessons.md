# Failure History And Lessons

## Executive summary

The current repo did not fail because the LLM-first idea was wrong. It failed
because implementation drift accumulated between several contracts:

- intended architecture versus live runtime
- semantic-stage artifacts versus surfaced final artifacts
- full-run truth versus filtered bundle projections
- summary metrics versus real artifact schema

The rewrite should treat those as the central lessons.

## Failure classes

## 1. Runtime/spec drift

Observed:

- reviewers expected staged policy machinery that no longer existed
- the live runtime moved to:
  - normalize
  - semantic_stage
  - semantic_review
  - aggregate_semantic_outputs
  - build context frames
  - generate teacher answers
  - build train/cache rows
  - build ledger rows
  - render/publish

Lesson:

- one runtime contract must be explicit and documented everywhere

## 2. Stale metrics

Observed:

- `entry_question_count` reported zero while beginner `what_is` questions were
  clearly present

Lesson:

- summaries must compute from live schemas, not stale field names

## 3. Provenance loss

Observed:

- question context retained support refs
- final surfaced answers still had empty provenance

Lesson:

- provenance must be first-class on authoritative records, not reconstructed at
  render time

## 4. Split answer ownership

Observed:

- teacher answers could exist in train/cache rows
- final rows still errored or diverged

Lesson:

- there must be one canonical answer object and one terminal row set

## 5. Bundle/export drift

Observed:

- filtered bundles previously mixed inconsistent course sets across artifacts
- manifest/log/file parity was not enforced

Lesson:

- one canonical selection object must drive every bundle artifact
- bundle validation must fail closed

## 6. Observability ambiguity

Observed:

- summaries reported zero LLM calls when logs were actually unavailable

Lesson:

- observability must distinguish:
  - no calls
  - usage unavailable
  - partial reporting
  - full reporting

## 7. Over-aggressive gating

Observed:

- a first attempt at hard entry-coverage gating blocked real runs on weak
  anchor heuristics

Lesson:

- new hard gates must be informational first, then proven against real slices

## Things the rewrite must avoid

- hidden fallback answer paths
- dual answer ownership
- late provenance reconstruction
- stale metrics reading obsolete fields
- filtered bundles treated as full-run truth
- hard gates based on unvalidated heuristics
