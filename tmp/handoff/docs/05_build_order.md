# Suggested Build Order

## Goal

Give the new team a practical sequence so they can build the replacement
pipeline without getting trapped in architecture-first paralysis.

## Phase 1: Foundations

Deliverables:

1. typed schemas for:
   - normalized course
   - semantic topics/questions/answers
   - generated questions
   - question context frames
   - answer records
   - train/cache rows
   - ledger/final rows
2. preflight
3. normalization
4. deterministic slice selection

Acceptance:

- schema unit tests pass
- preflight and normalization tests pass

## Phase 2: Semantic core

Deliverables:

1. full-course semantic prompt
2. semantic response normalization
3. semantic topics/questions/answers artifact writing
4. semantic review pass

Acceptance:

- semantic stage writes valid rows
- question families and source refs are present

## Phase 3: Canonicalization and policy

Deliverables:

1. family mapping
2. dedupe rules
3. informational coverage/anchor reporting
4. generated question validations

Important:

- coverage should be informational first
- do not make it blocking until real slices validate the heuristic

Acceptance:

- generated questions preserve ids and source refs
- `what_is` entry mapping works

## Phase 4: Context and answers

Deliverables:

1. course context frames
2. question context frames
3. teacher answer generation
4. canonical answer merge logic

Acceptance:

- question context carries support refs
- answer records preserve source refs

## Phase 5: Terminal products

Deliverables:

1. `train_rows.jsonl`
2. `cache_rows.jsonl`
3. `answers.jsonl`
4. `all_rows.jsonl`
5. per-course YAML bundle

Acceptance:

- shared artifacts and per-course YAML derive from same terminal row set
- answered rows do not silently disappear

## Phase 6: Publish and summaries

Deliverables:

1. merged publish into `data/final`
2. `run_summary.yaml`
3. LLM usage logging and pricing snapshot handling
4. summary rebuild from artifacts

Acceptance:

- publish preserves non-overlapping courses
- summary distinguishes unavailable usage from zero calls

## Phase 7: Inspection bundles

Deliverables:

1. canonical bundle selection object
2. filtered and full export modes
3. manifest
4. `bundle_validation.json`
5. `bundle_validation.md`

Acceptance:

- filtered bundles cannot mix course sets across artifacts
- bundle validation fails closed

## Phase 8: Real-data rollout

Deliverables:

1. first 1% smoke run
2. one 5% incremental publish sequence
3. filtered and full bundle validation on published outputs
4. only after that, consider enabling stricter coverage gates

Acceptance:

- real slices succeed
- provenance survives
- summary metrics are believable
- bundles validate
