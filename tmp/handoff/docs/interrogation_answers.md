# Interrogation Answers

## Scope note

`docs/interrogation.md` names `project_spec.md` and
`question_generation_algorithm_spec.md` as the canonical contract, but those
files do not exist in this checkout. The live contract evidence in this repo is
therefore the runtime code plus the active docs around the synthetic pipeline:

- [src/course_pipeline/flows/course_question_pipeline.py](/code/src/course_pipeline/flows/course_question_pipeline.py:1)
- [docs/pipeline-arch-v1.md](/code/docs/pipeline-arch-v1.md:1)
- [docs/clean_sheet_spec.md](/code/docs/clean_sheet_spec.md:1)
- [AGENTS.md](/code/AGENTS.md:1)

The answers below are based on the actual executed code path and the latest
available inspected run artifacts in
[`tmp/inspectgion_bundl_16`](/code/tmp/inspectgion_bundl_16).

## 1. Why does `source_run_summary.yaml` report `entry_question_count: 0`?

- Function/file:
  - `_quality_metrics()` in [src/course_pipeline/tasks/render.py](/code/src/course_pipeline/tasks/render.py:586)
- Fields involved:
  - reads `semantic_topic_questions.jsonl`
  - counts `sum(row.get("family") == "entry" for row in single_questions)`
- What is happening:
  - current semantic question rows do not have a `family` field
  - they have `question_family`, typically `"what_is"`, `"why_is"`, etc.
  - example from the real bundle:
    - `semantic_topic_questions.jsonl` for course `7630` contains
      `"question_family": "what_is"` for `"What is R?"` and
      `"What is a factor in R?"`
- Classification:
  - metric bug
- Minimal patch:
  - change `_quality_metrics()` to count canonical entry families from
    `question_family`, not a nonexistent `family` field
  - minimal safe version:
    - treat `question_family == "what_is"` as entry
- Regression test:
  - add a test where `semantic_topic_questions.jsonl` contains
    `"question_family": "what_is"` rows and assert `entry_question_count > 0`

## 2. Where is `entry_question_count` computed, and what exact predicate is used?

- Function/file:
  - `_quality_metrics()` in [src/course_pipeline/tasks/render.py](/code/src/course_pipeline/tasks/render.py:586)
- Exact predicate:
  - `sum(row.get("family") == "entry" for row in single_questions)`
- Classification:
  - metric bug because the predicate does not match the current artifact schema
- Minimal patch:
  - replace the predicate with canonical-family mapping over `question_family`
- Regression test:
  - unit test directly against `_quality_metrics()` through
    `rebuild_run_summary()`

## 3. Are `"what_is"` questions being mapped to Stage 11 family tag `entry`?

- Functions/files:
  - `_normalize_question_items()` in
    [src/course_pipeline/tasks/semantic_stage.py](/code/src/course_pipeline/tasks/semantic_stage.py:106)
  - `semantic_questions_to_generated_questions()` in
    [src/course_pipeline/tasks/aggregate_semantic_outputs.py](/code/src/course_pipeline/tasks/aggregate_semantic_outputs.py:95)
- Fields involved:
  - `SemanticQuestion.question_family`
  - `GeneratedQuestion.family`
- What is happening:
  - `"what_is"` remains `"what_is"`
  - it is copied directly into `GeneratedQuestion.family`
  - there is no promotion step to a canonical taxonomy like `entry`
- Classification:
  - pipeline path drift / spec mismatch
- Minimal patch:
  - add a canonical family mapping layer after semantic question generation
  - at minimum map `"what_is"` single-topic questions to `entry`
- Regression test:
  - semantic question with `question_family="what_is"` should produce a generated
    question or validation row with canonical family `entry`

## 4. Where are question families assigned in the latest operational path?

- Functions/files:
  - `run_semantic_stage_for_course()` ->
    `_normalize_question_items()` in
    [src/course_pipeline/tasks/semantic_stage.py](/code/src/course_pipeline/tasks/semantic_stage.py:106)
  - semantic review rewrite normalization in
    `_normalize_question_rewrite_payload()` in
    [src/course_pipeline/tasks/aggregate_semantic_outputs.py](/code/src/course_pipeline/tasks/aggregate_semantic_outputs.py:347)
  - propagation to generated questions in
    `semantic_questions_to_generated_questions()` in
    [src/course_pipeline/tasks/aggregate_semantic_outputs.py](/code/src/course_pipeline/tasks/aggregate_semantic_outputs.py:95)
  - propagation to ledger rows in
    `build_ledger_rows()` in
    [src/course_pipeline/tasks/build_ledger.py](/code/src/course_pipeline/tasks/build_ledger.py:11)
- Actual path:
  - semantic stage assigns `question_family`
  - optional semantic review may rewrite it
  - aggregate copies it into `GeneratedQuestion.family`
  - ledger copies `question.family` into `LedgerRow.question_family`
- Not happening:
  - normalization does not assign question family
  - there is no V4/V4.1 family policy stage in the runtime
  - summary rendering does not canonicalize family; it miscounts
- Classification:
  - expected behavior for current runtime, but inconsistent with the old staged spec
- Minimal patch:
  - add a canonical-family mapping step before validation/ledger
- Regression test:
  - end-to-end flow test asserting `what_is` becomes `entry` in final metrics

## 5. For course `7630`, do any generated questions get marked `required_entry=true`?

- Functions/files:
  - searched current runtime under `src/course_pipeline`
- Fields involved:
  - no `required_entry` field exists in current active schemas
- What is happening:
  - no
  - there is no active field or stage that marks any question
    `required_entry=true`
- Classification:
  - pipeline path drift / spec mismatch
- Minimal patch:
  - add `required_entry: bool = False` to the relevant question/validation
    schema and set it in a post-semantic policy stage
- Regression test:
  - course fixture with beginner foundational questions should set
    `required_entry=True` on at least one single-topic question per anchor

## 6. Is foundational anchor detection running at all for these 5 courses?

- Functions/files:
  - searched current runtime under `src/course_pipeline`
  - there is no active foundational-anchor detection task in the runtime call graph
- Actual anchors detected for these 5 courses:
  - none as a formal anchor artifact, because no anchor stage runs
- What does run instead:
  - semantic topic extraction in `semantic_stage`
  - for course `7630`, the semantic topic list contains:
    - `r`
    - `vectors`
    - `matrices`
    - `factors`
    - `data frames`
    - `lists`
  - but those are semantic topics, not foundational anchors
- Classification:
  - pipeline path drift / spec mismatch
- Minimal patch:
  - either reintroduce a small anchor-detection stage after semantic topics
  - or explicitly redefine the contract so semantic topics are the anchor source
- Regression test:
  - fixture run asserting anchor output exists and includes beginner primitives
    for all five courses

## 7. If foundational anchor detection does run, why did it miss obvious anchors?

- Short answer:
  - it does not run
- Code evidence:
  - no active task or helper invocation for foundational anchor detection exists
    in [src/course_pipeline/flows/course_question_pipeline.py](/code/src/course_pipeline/flows/course_question_pipeline.py:1)
  - `rg` over `src/course_pipeline` finds no active `required_entry` or anchor
    logic
- Classification:
  - not an anchor-quality bug; it is a missing-stage bug
- Minimal patch:
  - same as answer 6
- Regression test:
  - same as answer 6

## 8. Is `foundational_entry_questions.py` invoked on the current path?

- Code evidence:
  - no such active file exists at
    `src/course_pipeline/tasks/foundational_entry_questions.py`
  - no invocation exists in the runtime flow
- Answer:
  - no
- Classification:
  - pipeline path drift / spec mismatch
- Minimal patch:
  - either restore a real post-semantic foundational-entry stage or remove it
    from docs/specs
- Regression test:
  - add a call-graph-level flow test asserting the protected-entry stage either
    runs or the docs have been updated to remove it

## 9. Does the current path skip V4.1 protected-entry promotion?

- Function/file:
  - runtime call graph in
    [src/course_pipeline/flows/course_question_pipeline.py](/code/src/course_pipeline/flows/course_question_pipeline.py:97)
- Real executed path:
  - `normalize`
  - `semantic_stage`
  - `semantic_review`
  - `aggregate_semantic_outputs`
  - `build_course_context_frame`
  - `build_question_context_frames`
  - `generate_teacher_answers`
  - `build_train_rows`
  - `build_cache_rows`
  - `build_ledger_rows`
  - `persist_stage_artifacts`
  - `rebuild_run_summary`
  - optional `publish_final_outputs`
- Answer:
  - yes
  - there is no V4/V4.1 protected-entry promotion step on the live path
- Classification:
  - pipeline path drift / spec mismatch
- Minimal patch:
  - add a single post-semantic policy task before answer generation
- Regression test:
  - flow test proving protected entry promotion changes outputs before teacher
    answer generation

## 10. Where do `source_refs` first become empty for generated semantic questions?

- Functions/files:
  - semantic question normalization in
    `_normalize_question_items()` in
    [src/course_pipeline/tasks/semantic_stage.py](/code/src/course_pipeline/tasks/semantic_stage.py:106)
  - conversion to generated questions in
    `semantic_questions_to_generated_questions()` in
    [src/course_pipeline/tasks/aggregate_semantic_outputs.py](/code/src/course_pipeline/tasks/aggregate_semantic_outputs.py:95)
- Fields involved:
  - `SemanticQuestion.source_refs`
  - `GeneratedQuestion` has no `source_refs` field
- What the latest run shows:
  - already in `semantic_topic_questions.jsonl`, many generated semantic
    questions have `source_refs: []`
  - example `7630 / sq_012 / "What is a factor in R?"` has `source_refs: []`
- Answer:
  - they are absent at generation time for these question rows
  - then they are also dropped structurally because `GeneratedQuestion` cannot
    carry them
- Classification:
  - provenance wiring bug
- Minimal patch:
  - add `source_refs: list[str]` to `GeneratedQuestion`
  - copy `SemanticQuestion.source_refs` into it
- Regression test:
  - semantic question fixture with `source_refs=["chapter:4"]` must preserve it
    into generated question rows

## 11. End-to-end trace for course `7630` / `"What is a factor in R?"`

- Semantic question artifact:
  - [tmp/inspectgion_bundl_16/semantic_topic_questions.jsonl](/code/tmp/inspectgion_bundl_16/semantic_topic_questions.jsonl:1)
  - fields:
    - `question_id: "sq_012"`
    - `question_family: "what_is"`
    - `relevant_topics: []`
    - `source_refs: []`
- Question context frame:
  - [tmp/inspectgion_bundl_16/question_context_frames.jsonl](/code/tmp/inspectgion_bundl_16/question_context_frames.jsonl:1)
  - fields:
    - `support_refs: ["summary", "overview"]`
    - `relevant_topics: []`
- Train row:
  - [tmp/inspectgion_bundl_16/train_rows.jsonl](/code/tmp/inspectgion_bundl_16/train_rows.jsonl:1)
  - fields:
    - `provided_context.question_context_frame.support_refs: ["summary", "overview"]`
    - no `source_refs`
- Cache row:
  - [tmp/inspectgion_bundl_16/cache_rows.jsonl](/code/tmp/inspectgion_bundl_16/cache_rows.jsonl:1)
  - same context retention, still no `source_refs`
- Answer row:
  - [tmp/inspectgion_bundl_16/answers.jsonl](/code/tmp/inspectgion_bundl_16/answers.jsonl:1)
  - fields:
    - `evidence: []`
    - `provenance.topic_labels: []`
- Final row:
  - [tmp/inspectgion_bundl_16/all_rows.jsonl](/code/tmp/inspectgion_bundl_16/all_rows.jsonl:1)
  - fields:
    - `source_evidence: []`
- Exact drop points:
  - `source_refs` empty already in semantic question output
  - `GeneratedQuestion` does not preserve `source_refs`
  - `semantic_answers_to_records()` creates `AnswerRecord.evidence=[]`
  - `build_ledger_rows()` copies `answer.evidence` to `LedgerRow.source_evidence`
- Classification:
  - provenance wiring bug
- Minimal patch:
  - preserve `source_refs` from semantic question into generated question,
    answer record, and ledger row
- Regression test:
  - fixture for `"What is a factor in R?"` with `source_refs=["chapter:4"]` must
    end with non-empty provenance in `answers.jsonl` and `all_rows.jsonl`

## 12. Why are `support_refs` not carried into `source_refs` or `source_evidence`?

- Functions/files:
  - `_infer_support_refs()` in
    [src/course_pipeline/tasks/build_question_context.py](/code/src/course_pipeline/tasks/build_question_context.py:161)
  - `build_train_rows()` in
    [src/course_pipeline/tasks/build_product_rows.py](/code/src/course_pipeline/tasks/build_product_rows.py:8)
  - `semantic_answers_to_records()` in
    [src/course_pipeline/tasks/aggregate_semantic_outputs.py](/code/src/course_pipeline/tasks/aggregate_semantic_outputs.py:138)
  - `build_ledger_rows()` in
    [src/course_pipeline/tasks/build_ledger.py](/code/src/course_pipeline/tasks/build_ledger.py:11)
- What is happening:
  - `support_refs` lives only inside `QuestionContextFrame`
  - no code maps `support_refs` into answer provenance or ledger evidence
  - answer records are created from semantic answers without using question
    context frames
- Classification:
  - provenance wiring bug
- Minimal patch:
  - add a provenance merge step when building answer records or ledger rows:
    `support_refs -> source_refs/source_evidence`
- Regression test:
  - if a question context frame has `support_refs`, surfaced answer rows should
    not have empty provenance

## 13. Is there a schema mismatch between `support_refs`, `source_refs`, and `source_evidence`?

- Files:
  - [src/course_pipeline/schemas.py](/code/src/course_pipeline/schemas.py:1)
- Mismatch:
  - `QuestionContextFrame.support_refs: list[str]`
  - `SemanticQuestion.source_refs: list[str]`
  - `LedgerRow.source_evidence: list[TopicEvidence]`
  - `AnswerRecord.evidence: list[TopicEvidence]`
- Answer:
  - yes
  - string refs and structured evidence are different types and there is no
    adapter between them
- Classification:
  - provenance wiring bug
- Minimal patch:
  - pick one canonical provenance representation
  - lowest-cost patch:
    - add `source_refs: list[str]` to `AnswerRecord` and `LedgerRow`
    - keep `source_evidence` optional until there is a real converter
- Regression test:
  - schema round-trip test proving refs survive from semantic question through
    final row

## 14. Which code path renders `answers.jsonl` and `all_rows.jsonl`, and why is provenance empty?

- Functions/files:
  - `persist_stage_artifacts()` in
    [src/course_pipeline/tasks/render.py](/code/src/course_pipeline/tasks/render.py:72)
  - `build_ledger_rows()` in
    [src/course_pipeline/tasks/build_ledger.py](/code/src/course_pipeline/tasks/build_ledger.py:11)
  - `semantic_answers_to_records()` in
    [src/course_pipeline/tasks/aggregate_semantic_outputs.py](/code/src/course_pipeline/tasks/aggregate_semantic_outputs.py:138)
- Why empty:
  - `answers.jsonl` is written from `AnswerRecord`
  - semantic answer records are created with `evidence=[]`
  - `all_rows.jsonl` is written from `LedgerRow`
  - ledger rows copy `answer.evidence`, which is empty
  - teacher-answer fallback branch in `build_ledger_rows()` also hardcodes
    `source_evidence=[]`
- Classification:
  - provenance wiring bug
- Minimal patch:
  - populate answer evidence or source refs before render
- Regression test:
  - render test asserting surfaced answered rows include non-empty provenance
    when upstream refs exist

## 15. Is the empty-provenance issue render-only?

- Answer:
  - no
- Code evidence:
  - authoritative in-memory `AnswerRecord` already has `evidence=[]`
  - authoritative `GeneratedQuestion` lacks `source_refs`
  - authoritative `LedgerRow` receives empty evidence before export
- Classification:
  - provenance wiring bug in authoritative records, not just export
- Minimal patch:
  - fix upstream models, not just rendering
- Regression test:
  - unit tests on `semantic_answers_to_records()` and `build_ledger_rows()`

## 16. Which invariant is being violated?

- Invariant:
  - surfaced questions/answers should preserve course-derived provenance into
    final inspection artifacts
- Violating modules:
  - `semantic_questions_to_generated_questions()` drops question-level refs
  - `semantic_answers_to_records()` does not construct evidence from refs
  - `build_ledger_rows()` emits empty `source_evidence` for teacher fallback
- Classification:
  - provenance wiring bug
- Minimal patch:
  - preserve provenance through generated question -> answer -> ledger
- Regression test:
  - full flow fixture with non-empty semantic `source_refs`

## 17. Why did the run not fail in strict mode if `entry_question_count` is 0?

- Answer:
  - because there is no active strict coverage enforcement path in the runtime
- Code evidence:
  - no strict coverage check is called in
    [src/course_pipeline/flows/course_question_pipeline.py](/code/src/course_pipeline/flows/course_question_pipeline.py:97)
  - `entry_question_count` is only a summary metric in
    `_quality_metrics()`; it does not gate the run
- Classification:
  - pipeline path drift / spec mismatch
- Minimal patch:
  - add a pre-publish coverage assertion after question generation or after
    ledger build
- Regression test:
  - flow fixture should fail when required entry coverage is missing

## 18. Where is strict coverage failure enforced in code?

- Answer:
  - nowhere in the active runtime
- Code evidence:
  - no active function in `src/course_pipeline` performs strict coverage gating
    on entry coverage
- Classification:
  - pipeline path drift / spec mismatch
- Minimal patch:
  - add a dedicated coverage-audit task returning a structured report and raise
    on failure
- Regression test:
  - direct unit test of the new coverage audit

## 19. Could coverage auditing scope explain visible beginner definitions but zero coverage?

- Answer:
  - not in the current runtime, because there is no active coverage audit
  - the visible contradiction comes from the summary metric bug:
    - visible beginner definition questions exist
    - `entry_question_count` still reads zero because it checks the wrong field
- Classification:
  - metric bug plus path drift
- Minimal patch:
  - fix the metric now
  - add a real coverage audit separately
- Regression test:
  - summary metric test plus coverage-audit test

## 20. Why was `24370` excluded from the filtered bundle?

- Functions/files:
  - `_random_inspectgion_selection()` in
    [src/course_pipeline/cli.py](/code/src/course_pipeline/cli.py:132)
  - `mk_inspectgion_bundle()` in
    [src/course_pipeline/cli.py](/code/src/course_pipeline/cli.py:535)
- What happened in the latest bundle:
  - bundle `16` uses `random.Random(int(bundle_id))`
  - with `bundle_id=16`, the sampled 4-course set was:
    - `24372`
    - `24373`
    - `24374`
    - `7630`
  - `24370` was not sampled
- Classification:
  - expected filtered-bundle behavior
- Minimal patch:
  - none for correctness
  - if full-latest inspection is desired, default export mode should be `full`
- Regression test:
  - CLI test already covers filtered bundle selection behavior

## 21. Is the filtered inspection bundle expected behavior, or masking problems?

- Answer:
  - filtered mode is expected behavior today
  - but it can mislead reviewers if they assume the bundle is the full latest run
- Code evidence:
  - `mk_inspectgion_bundle()` default is `export_mode="filtered"`
- Classification:
  - expected behavior with observability risk
- Minimal patch:
  - either default to `full` for latest-run QA
  - or make the filtered summary/manifest wording more explicit
- Regression test:
  - test that manifest and bundle log explicitly declare `export_mode: filtered`

## 22. Which command/config/default selected 4 courses and 98 of 146 rows?

- Entrypoint:
  - `python -m course_pipeline.cli mk_inspectgion_bundle 16`
- Default:
  - `export_mode="filtered"` in
    [src/course_pipeline/cli.py](/code/src/course_pipeline/cli.py:538)
- Selection logic:
  - `_random_inspectgion_selection(source_dir, bundle_id, course_count=4)`
  - samples 4 course YAML files deterministically from the bundle id seed
  - row artifacts are then filtered by the canonical selection object
- Classification:
  - expected behavior
- Minimal patch:
  - same as answer 21
- Regression test:
  - test filtered and full modes separately

## 23. Are there discrepancies between authoritative full-run artifacts and the filtered bundle?

- Answer:
  - yes by design in counts and course coverage
  - no longer by accidental mixed selection within the bundle itself
- Code evidence:
  - `source_run_summary.yaml` in bundle `16` shows 5 courses and 146 rows
  - bundle `run_summary.yaml` shows 4 courses and 98 rows
  - current exporter writes both, plus manifest and validation report
- Classification:
  - expected behavior, but historically this was easy to misread
- Minimal patch:
  - keep `source_run_summary.yaml` plus filtered `run_summary.yaml`
  - consider making `mk_inspectgion_bundle --export-mode full` the QA default
- Regression test:
  - test that filtered bundle includes both source-run and bundle-level summary

## 24. What is the true authoritative artifact for debugging?

- Precedence order:
  1. semantic generation/debug:
     - `semantic_topics.jsonl`
     - `semantic_topic_questions.jsonl`
     - `semantic_correlated_topic_questions.jsonl`
     - `semantic_synthetic_answers.jsonl`
  2. runtime answer-serving context:
     - `question_context_frames.jsonl`
     - `train_rows.jsonl`
     - `cache_rows.jsonl`
  3. canonical published surfaced answers:
     - `answers.jsonl`
     - `all_rows.jsonl`
  4. bundle:
     - inspection bundle is a projection of published artifacts, not the source
       of truth
- Code references:
  - generation path:
    [src/course_pipeline/flows/course_question_pipeline.py](/code/src/course_pipeline/flows/course_question_pipeline.py:97)
  - persistence path:
    [src/course_pipeline/tasks/render.py](/code/src/course_pipeline/tasks/render.py:72)
- Classification:
  - expected architecture, but reviewers should not treat a filtered bundle as
    the full-run authority
- Minimal patch:
  - document this precedence explicitly
- Regression test:
  - doc/test not essential; bundle tests already prevent mixed selection

## 25. Is the repo currently running the canonical spec path, or a drifted runtime?

- Answer:
  - drifted runtime
- Real call graph:
  - `normalize`
  - `semantic_stage`
  - `semantic_review`
  - `aggregate_semantic_outputs`
  - `build_course_context_frame`
  - `build_question_context_frames`
  - `generate_teacher_answers`
  - `build_train_rows`
  - `build_cache_rows`
  - `build_ledger_rows`
  - render/publish
- Missing from runtime:
  - explicit V3/V4/V4.1 policy and protected-entry stages
  - strict coverage audit/fail step
- Classification:
  - pipeline path drift / spec mismatch
- Minimal patch:
  - restore one explicit post-semantic policy stage rather than many legacy
    shims
- Regression test:
  - flow-level call-path expectations around policy outputs

## 26. Smallest change to restore spec-compliant behavior

### 26a. Entry-family tagging

- Minimal patch:
  - add canonical-family mapping after semantic question generation
  - map single-topic `"what_is"` to `entry`
- Test:
  - beginner definition questions count as entry

### 26b. Protected entry promotion

- Minimal patch:
  - add one post-semantic policy task that tags and preserves required entry
    questions before answer generation
- Test:
  - fixture course with foundational topics yields protected entry rows

### 26c. Strict coverage failure

- Minimal patch:
  - add a coverage audit after policy tagging and raise before publish if entry
    coverage is missing
- Test:
  - flow should fail when protected entry coverage is zero

### 26d. Provenance propagation

- Minimal patch:
  - carry `source_refs` from semantic questions into generated questions, then
    into answers and final rows
  - if `source_evidence` stays typed as `TopicEvidence`, add a parallel
    `source_refs` field to final rows
- Test:
  - surfaced rows cannot have empty provenance when upstream refs exist

## 27. What regression fixtures should be added immediately?

- `entry_metric_counts_what_is_questions`
  - semantic single-topic questions with `question_family="what_is"`
  - assert `entry_question_count > 0`
- `protected_entry_policy_fixture`
  - beginner course with foundational topics
  - assert required/protected entry tagging exists
- `strict_coverage_failure_fixture`
  - beginner course missing entry coverage
  - assert run fails before publish
- `provenance_round_trip_fixture`
  - semantic question with non-empty `source_refs`
  - assert:
    - question context support refs not empty
    - answer provenance not empty
    - final row provenance not empty
- `filtered_bundle_not_full_run_fixture`
  - assert filtered bundle summaries and manifest clearly differ from source run

## 28. What is the single root cause?

- Conclusion:
  - multiple independent bugs, with one dominant umbrella cause:
    pipeline path drift / spec mismatch
- Why:
  - metric bug:
    - `entry_question_count` counts the wrong field
  - provenance wiring bug:
    - refs are absent/dropped and never propagated into final surfaced rows
  - spec mismatch:
    - no active protected-entry stage
    - no active strict coverage enforcement
    - no active foundational-anchor stage
  - bundle/export behavior:
    - filtered bundles are expected today, but can confuse reviewers if treated
      as full-run artifacts
- Strongest code evidence:
  - live runtime in
    [src/course_pipeline/flows/course_question_pipeline.py](/code/src/course_pipeline/flows/course_question_pipeline.py:97)
    contains no V4/V4.1 policy or coverage stage
  - summary metric in
    [src/course_pipeline/tasks/render.py](/code/src/course_pipeline/tasks/render.py:601)
    counts `row.get("family") == "entry"`
  - provenance is dropped or never built in:
    - [src/course_pipeline/tasks/aggregate_semantic_outputs.py](/code/src/course_pipeline/tasks/aggregate_semantic_outputs.py:95)
    - [src/course_pipeline/tasks/aggregate_semantic_outputs.py](/code/src/course_pipeline/tasks/aggregate_semantic_outputs.py:138)
    - [src/course_pipeline/tasks/build_ledger.py](/code/src/course_pipeline/tasks/build_ledger.py:11)

The shortest honest answer is:

- the pipeline is not generically "broken"
- the core semantic-to-answer run is succeeding
- but the runtime has drifted away from the older staged spec, and that drift
  left behind:
  - one bad summary metric
  - one missing protected-entry/coverage stage
  - one real provenance propagation bug
