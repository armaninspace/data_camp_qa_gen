# Target Pipeline Spec

## Goal

Turn scraped course metadata into one canonical set of learner-facing question
and answer rows, plus training/cache artifacts and inspection outputs.

Primary final row shape:

`<course, relevant_topics, question_text, question_answer, correctness, source_refs>`

## Core rules

1. One canonical answer path.
2. No old grounded brochure-span answer path.
3. Shared artifacts and per-course YAML derive from the same terminal row set.
4. Full-run truth and bundle truth are explicitly separated.
5. Provenance is mandatory on authoritative records.

## End-to-end runtime

```text
raw course
-> preflight
-> normalized course
-> full-course semantic stage
-> semantic review
-> semantic policy / canonicalization / dedupe
-> context frames
-> answer generation
-> product rows
-> terminal row assembly
-> render per-run artifacts
-> publish merged final outputs
-> optional inspection bundle projection
```

## Canonical artifacts

Per-run:

- `excluded_courses.jsonl`
- `normalized_courses.jsonl`
- `course_context_frames.jsonl`
- `question_context_frames.jsonl`
- `semantic_topics.jsonl`
- `semantic_correlated_topics.jsonl`
- `semantic_topic_questions.jsonl`
- `semantic_correlated_topic_questions.jsonl`
- `semantic_synthetic_answers.jsonl`
- `semantic_review_decisions.jsonl`
- `train_rows.jsonl`
- `cache_rows.jsonl`
- `answers.jsonl`
- `all_rows.jsonl`
- `course_yaml/<course_id>.yaml`
- `run_summary.yaml`
- `logs/llm_calls.jsonl`
- `logs/pricing_snapshot.json`

Published:

- merged artifact family in `data/final`

Bundle:

- filtered or full projection of published outputs
- manifest plus validation artifacts

## Stage contracts

## Stage 0: Preflight

Input:

- raw course YAML/JSON

Output:

- `PreflightCourseDecision`

Required fields:

- `course_id`
- `source_path`
- `quality_status`
- `exclude_reason`
- `title_raw`
- `overview_present`
- `syllabus_count`

Invariant:

- every raw course receives one preflight decision

## Stage 1: Normalize

Input:

- raw course

Output:

- `NormalizedCourse`

Required fields:

- `course_id`
- `title`
- `provider`
- `summary`
- `overview`
- `chapters`
- `metadata`
- `source_refs`

Invariant:

- normalization preserves source-bearing text and marks inferred structure

## Stage 2: Full-course semantic stage

Input:

- one entire normalized course

Output:

- semantic topics
- correlated topics
- single-topic questions
- correlated-topic questions
- short synthetic answers

Semantic question required fields:

- `question_id`
- `question_text`
- `question_family`
- `relevant_topics`
- `question_scope`
- `rationale`
- `source_refs`

Semantic topic required fields:

- `label`
- `normalized_label`
- `topic_type`
- `confidence`
- `course_centrality`
- `source_refs`
- `rationale`

Invariant:

- semantic output is structured, typed, and always carries schema-valid family
  and source-ref fields

## Stage 3: Semantic review

Input:

- normalized course
- semantic stage result

Output:

- semantic review decisions

Invariant:

- no silent deletion; editorial preferences do not hard-reject good rows

## Stage 4: Policy / canonicalization / dedupe

Input:

- reviewed semantic artifacts

Output:

- canonical topics
- generated questions
- validations
- informational coverage report

Required generated-question fields:

- `question_id`
- `question_text`
- `family`
- `generation_scope`
- `relevant_topics`
- `source_refs`
- `required_entry`
- `anchor_label`

Invariant:

- semantic `what_is` questions map to canonical entry semantics
- generated questions preserve provenance

## Stage 5: Context frames

Input:

- normalized course
- generated questions / semantic question payloads

Output:

- course context frame
- question context frames

Required `QuestionContextFrame` fields:

- `question_id`
- `course_id`
- `question_text`
- `question_intent`
- `relevant_topics`
- `chapter_scope`
- `expected_answer_shape`
- `scope_bias`
- `support_refs`

Invariant:

- every generated question gets one context frame

## Stage 6: Answer generation

Input:

- course context frame
- question context frames

Output:

- teacher answer drafts
- merged canonical answer records

Required answer fields:

- `question_id`
- `question_text`
- `answer_text`
- `answer_mode`
- `correctness`
- `source_refs`
- `provenance`

Invariant:

- one surfaced answered question corresponds to one canonical answer record

## Stage 7: Product rows

Output:

- `train_rows.jsonl`
- `cache_rows.jsonl`

Invariant:

- good Q/A pairs survive by default

## Stage 8: Terminal row assembly

Output:

- `LedgerRow[]`

Terminal states:

- `answered`
- `rejected`
- `errored`

Required final-row fields:

- `row_id`
- `course`
- `relevant_topics`
- `question_text`
- `question_answer`
- `correctness`
- `question_family`
- `status`
- `reject_reason`
- `source_refs`

Invariant:

- every generated question reaches one terminal state

## Stage 9: Render

Goal:

- write consistent shared artifacts and per-course YAML

Invariant:

- render fails if shared artifacts and per-course YAML disagree on terminal row
  set

## Stage 10: Publish

Goal:

- merge successful run outputs into `data/final`

Invariant:

- only overlapping courses are overwritten

## Stage 11: Inspection bundle

Goal:

- create reproducible QA/debug projection from published outputs

Invariant:

- one canonical selection object drives every artifact
- validation fails closed

## Truth precedence

1. full per-run artifacts
2. published merged `data/final`
3. inspection bundle projection

Filtered bundles are never the primary truth source.
