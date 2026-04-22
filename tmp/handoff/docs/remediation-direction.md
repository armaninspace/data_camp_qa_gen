You are working in the live runtime, not the older staged spec.

Treat the repo’s actual executed path as the source of truth for implementation:
normalize
-> semantic_stage
-> semantic_review
-> aggregate_semantic_outputs
-> build_course_context_frame
-> build_question_context_frames
-> generate_teacher_answers
-> build_train_rows
-> build_cache_rows
-> build_ledger_rows
-> persist/render/publish

Do not spend time trying to resurrect legacy V3/V4/V4.1 machinery wholesale.
Implement the smallest set of changes that makes the live runtime honest,
traceable, and coverage-aware.

## Objective

Stabilize the pipeline by fixing three things in this order:

1. the lying entry metric
2. provenance propagation through authoritative records
3. one minimal post-semantic policy/coverage stage

The goal is not a broad refactor. The goal is to make the current runtime
produce trustworthy summaries and inspectable outputs.

## Ground rules

- Debug against full-run artifacts, not filtered inspection bundles.
- A filtered bundle is only a projection and must not be treated as the
  authoritative surface for QA.
- Prefer small surgical patches over architecture rewrites.
- Preserve backward compatibility where practical.
- Add regression tests for each fix before or with the patch.

## Known facts from the latest investigation

1. `entry_question_count` is currently computed incorrectly.
   `_quality_metrics()` counts `row.get("family") == "entry"` from
   `semantic_topic_questions.jsonl`, but live semantic rows use
   `question_family` values like `"what_is"`.

2. The live runtime does not include a protected-entry stage, foundational
   anchor stage, or strict coverage enforcement stage.

3. Provenance is lost or absent across the runtime:
   - semantic question rows may already have empty `source_refs`
   - `GeneratedQuestion` does not preserve `source_refs`
   - `AnswerRecord` is created with empty evidence
   - `LedgerRow` copies empty evidence into final rows
   - `QuestionContextFrame.support_refs` exists but is never adapted into final
     answer/ledger provenance

4. Filtered bundles are expected behavior today, but they can mislead QA if
   mistaken for full-run output.

## Priority order

### Priority 1: Fix the entry metric

Patch the summary/quality metric so it reflects the actual current schema.

Implementation target:
- `src/course_pipeline/tasks/render.py`

Required change:
- update `_quality_metrics()` so entry questions are counted from the live
  family field, not a nonexistent `family` key
- minimal safe mapping:
  - single-topic `question_family == "what_is"` counts as entry

Deliverables:
- patch
- unit test that feeds semantic question rows with `question_family="what_is"`
  and asserts `entry_question_count > 0`

Do not overdesign this step. It is a metric fix.

### Priority 2: Fix provenance propagation end to end

Patch the authoritative data models and builders so source provenance survives
through:
semantic question -> generated question -> answer record -> ledger row

Implementation targets likely include:
- `src/course_pipeline/schemas.py`
- `src/course_pipeline/tasks/aggregate_semantic_outputs.py`
- `src/course_pipeline/tasks/build_ledger.py`
- any answer-building helpers used by the teacher-answer path

Required changes:
1. add `source_refs: list[str]` to `GeneratedQuestion`
2. add `source_refs: list[str]` to `AnswerRecord`
3. add `source_refs: list[str]` to `LedgerRow`
4. copy `SemanticQuestion.source_refs` into `GeneratedQuestion.source_refs`
5. when building answer records, preserve upstream `source_refs`
6. if semantic `source_refs` is empty but `QuestionContextFrame.support_refs`
   exists, merge those as fallback provenance into the answer/ledger layer
7. do not force a fake conversion into structured `TopicEvidence` if the repo
   does not currently have a reliable adapter; keep `source_evidence` as-is and
   make `source_refs` the canonical low-cost provenance path for now

Important:
- this is not a render-only bug
- fix the upstream authoritative records, not just JSONL emission

Deliverables:
- schema patch
- propagation patch
- regression tests:
  - semantic question with non-empty `source_refs` survives into final rows
  - question with empty semantic `source_refs` but non-empty context
    `support_refs` gets non-empty final `source_refs`
  - surfaced answered rows do not have empty provenance when upstream refs exist

### Priority 3: Add one minimal post-semantic policy stage

Insert a small policy task into the live runtime.
Do not recreate the full old staged architecture.
Add one explicit stage after semantic aggregation and before answer generation.

Preferred insertion point:
after `aggregate_semantic_outputs`
before `generate_teacher_answers`

This stage must do exactly four things:

1. canonical family mapping
   - map live semantic families into a runtime taxonomy
   - at minimum:
     - single-topic `"what_is"` -> `entry`

2. anchor source derivation
   - use existing semantic topics as the anchor source
   - do not build a new ontology system
   - if semantic topics for a beginner course include items like `r`, `vectors`,
     `matrices`, `factors`, `data frames`, `lists`, those are sufficient for a
     first-pass anchor set

3. required entry tagging
   - add `required_entry: bool = False` to the relevant schema(s)
   - mark the canonical beginner-definition question for each detected anchor as
     `required_entry=True`

4. strict coverage audit
   - before publish, fail the run if required entry coverage is missing for the
     detected anchor set
   - this should be an explicit runtime gate, not just a summary metric

Implementation note:
- this is a live-runtime replacement for the missing protected-entry /
  coverage stage
- keep it narrow and testable

Deliverables:
- new post-semantic policy task
- flow wiring patch in `src/course_pipeline/flows/course_question_pipeline.py`
- regression tests:
  - `what_is` beginner definitions become canonical `entry`
  - fixture course with beginner semantic topics yields at least one
    `required_entry=True` question per anchor
  - run fails before publish when required entry coverage is missing

## Bundle / QA behavior

Do not patch bundle selection logic for correctness unless necessary.
Filtered bundle behavior is expected today.

But do one of these:
1. make full export the QA default for latest-run inspection, or
2. make filtered mode impossible to misread by clearly labeling manifests and
   summaries as filtered projections

This is secondary to the three priorities above.
Only touch it after the metric/provenance/policy fixes are in.

## Acceptance criteria

The work is done when all of the following are true:

1. latest-run summary no longer reports `entry_question_count: 0` when
   beginner `what_is` questions exist

2. surfaced answered rows preserve provenance:
   - `answers.jsonl` has non-empty `source_refs` when upstream refs/support refs
     exist
   - `all_rows.jsonl` has non-empty `source_refs` when upstream refs/support
     refs exist

3. the live runtime has one explicit post-semantic policy stage that:
   - maps `what_is` to `entry`
   - tags required entries
   - enforces strict coverage before publish

4. regression tests cover:
   - entry metric correctness
   - provenance round trip
   - required-entry tagging
   - strict coverage failure
   - filtered bundle labeling or full-run QA default behavior

## Output format

Return:
1. a short diagnosis summary
2. the exact files changed
3. patch diffs
4. new tests added
5. the result of running the relevant test subset
6. any unresolved follow-up items, explicitly labeled as non-blocking

## One more constraint

If you discover additional legacy/spec mismatch, do not broaden scope unless it
blocks one of the three priorities above.
Document it, but keep the patch set focused.
