# Pipeline Architecture V1

## Purpose

This document describes the canonical V1 architecture for the reshaped
`course_pipeline`.

It supersedes the old split model where:

- deterministic code was the primary semantic extractor
- synthetic answers were layered on afterward
- stale grounded-answer assumptions still affected the runtime and artifacts

The V1 architecture is an LLM-first semantic pipeline.

Its purpose is to turn scraped course metadata into:

- normalized course records
- one canonical semantic-stage artifact family
- one canonical reviewed-question artifact family
- one canonical retained teacher-answer artifact family
- one canonical shared-answer artifact family derived from retained teacher answers
- one canonical final-row artifact family derived from the same retained answer set
- per-course YAML bundles
- merged published outputs in `data/final`
- inspection bundles filtered from published outputs

## Canonical Flow

The V1 flow is:

```text
raw course
  -> preflight validate
  -> normalize course
  -> full normalized course YAML
      -> primary LLM semantic pass
      -> optional LLM review pass
      -> deterministic transformation / dedupe / packaging / consistency only
  -> build course/question context frames
  -> generate teacher answers
  -> build train_rows + cache_rows
  -> derive shared answers + final rows from the same retained answer set
  -> render shared artifacts
  -> render per-course YAML
  -> rebuild run summary
  -> publish merged final outputs
  -> build inspection bundle from data/final
```

The LLM is the semantic front end.

Deterministic code remains responsible for:

- normalization
- aggregation
- canonicalization
- deduplication
- teacher-answer propagation
- final-row construction from retained answers
- consistency checks
- rendering
- publish and inspection workflows

Deterministic code is not the primary semantic judge in V1.

The semantic boundary is:

```text
full normalized course YAML
  -> primary LLM semantic pass
  -> optional LLM review pass
  -> deterministic transformation / dedupe / packaging / consistency only
```

## Design Principles

The implementation should follow these rules:

- one primary run command for final outputs
- one canonical semantic source for topics, relations, questions, and draft
  answers
- one canonical answer path for final published outputs
- full normalized course YAML as the semantic-stage input
- optional second LLM pass for review-and-repair
- deterministic downstream stages only for transformation and integrity work
- file-first inspectable artifacts over hidden state
- `course_id` as the merge and upsert key
- overlap-safe publish semantics
- fail-fast consistency checks before publish

## Repo Components

Expected package layout after the reshape:

```text
src/course_pipeline/
  cli.py
  config.py
  llm.py
  schemas.py
  run_logging.py
  flows/
    course_question_pipeline.py
  tasks/
    normalize.py
    preflight_validate.py
    semantic_stage.py
    semantic_review.py
    canonicalize.py
    aggregate_semantic_outputs.py
    build_final_rows.py
    render.py
  prompts/
    semantic_stage.md
    semantic_review.md
```

Notes:

- exact module names may differ slightly during implementation
- the architecture should converge on these responsibilities
- `answer_questions.py` is not part of the V1 runtime design
- the old deterministic semantic extractor is not the canonical semantic source

## High-Level Data Model

The V1 model centers on a semantic-stage bundle.

Key records:

- `NormalizedCourse`
- `SemanticStageResult`
- `SemanticTopic`
- `SemanticCorrelatedTopic`
- `SemanticQuestion`
- `SemanticSyntheticAnswer`
- `SemanticReviewDecision`
- `CanonicalTopic`
- `QuestionValidationRecord`
- `SyntheticAnswerValidationRecord`
- `TeacherAnswerDraft`
- `TrainRow`
- `CacheRow`
- `AnswerRecord`
- `LedgerRow`
- `CourseBundle`
- `PreflightCourseDecision`

Relationship sketch:

```text
raw course
  -> NormalizedCourse
  -> SemanticStageResult
      -> SemanticTopic*
      -> SemanticCorrelatedTopic*
      -> SemanticQuestion*
      -> SemanticSyntheticAnswer*
  -> SemanticReviewDecision*
  -> CanonicalTopic*
  -> QuestionValidationRecord*
  -> SyntheticAnswerValidationRecord*
  -> TeacherAnswerDraft*
  -> TrainRow*
  -> CacheRow*
  -> AnswerRecord*
  -> LedgerRow*
  -> CourseBundle
```

## Stage-by-Stage Description

### 0. Preflight Validation

Purpose:

- classify each raw course as `usable`, `partial`, or `broken`
- exclude malformed or content-empty records before semantic processing
- preserve machine-readable exclusion records

Rules:

- `broken` courses do not enter the main semantic flow
- `usable` and `partial` may continue
- exclusions are run-scoped diagnostics and are not published to `data/final`

Expected outputs:

- `excluded_courses.jsonl`
- preflight quality counts for logging and run summary

### 1. Normalize Course

Purpose:

- coerce raw scraped records into one normalized course schema
- preserve title, course id, overview, summary, syllabus, metadata, and source
  references
- produce a stable YAML-like object suitable for the semantic stage

Important property:

- the full normalized course YAML is the primary semantic substrate
- it must preserve enough structure for the model to reason about centrality,
  repetition, chapter relationships, and wrapper language

### Full-Course Semantic Boundary

Purpose:

- use the entire normalized course YAML as one coherent semantic context
- produce the primary structured semantic bundle for learner-facing outputs

Input:

- the full normalized course YAML

Output sections:

- `topics`
- `correlated_topics`
- `topic_questions`
- `correlated_topic_questions`
- `synthetic_answers`

The prompt must explicitly instruct the model to:

- identify real learner-facing topics
- identify heavily correlated topics
- generate only natural basic learner questions
- generate short synthetic tutor answers from general knowledge
- reject wrapper language, onboarding phrases, discourse fragments, narrative
  stray words, marketing phrases, and vague activity headings
- return structured JSON only

Regression examples that the prompt should explicitly reject:

- `where`
- `getting started in python`
- `different types of plots`
- `learn to manipulate dataframes`

Positive-control examples the prompt should recover when supported:

- `pandas`
- `matplotlib`
- `dictionary`
- `control flow`
- `loop`
- `filtering`

### Optional LLM Review Pass

Purpose:

- review the first semantic bundle as critic, editor, merger, and rejector
- improve quality without replacing the primary semantic context

Input:

- the same full normalized course YAML
- the full structured bundle from the primary semantic pass

Allowed decisions:

- `keep`
- `rewrite`
- `merge`
- `reject`

The review pass may operate on:

- topics
- correlated topics
- single-topic questions
- correlated-topic questions
- synthetic answers

Important rule:

- if the second pass is present, it is the semantic review layer
- deterministic code should not duplicate that semantic judgment afterward

### Deterministic Transformation, Aggregation, and Dedupe

Purpose:

- normalize labels and aliases
- collapse duplicate items
- aggregate semantically equivalent outputs into canonical records
- preserve provenance from the semantic-stage outputs

Allowed downstream operations at this point:

- normalization
- canonicalization
- alias collapse
- deduplication
- aggregation

Disallowed downstream behavior:

- re-deriving topics from chapter headings as a competing semantic source
- deterministic generation of new topics, questions, or answers as the primary
  architecture

### Final Question and Answer Validation

Purpose:

- preserve one canonical accepted/rejected view for questions and synthetic
  answers before final-row construction

This validation layer may still enforce:

- structural validity
- duplicate suppression
- malformed-question rejection
- answer-schema validity
- answer-mode integrity
- contradiction or rewrite decisions from the review pass

But it should not act as a replacement semantic generator.

### 6. Final Row Construction

Purpose:

- build one canonical terminal row set for publish and per-course rendering
- use retained teacher answers as the fallback answer source when semantic shared
  answers are absent
- keep shared `answers.jsonl` and final rows aligned to the same retained answer
  set

Final row states:

- `answered`
- `rejected`
- `errored`

Rules:

- final rows are the terminal representation of the course
- shared artifacts and per-course YAML must derive from the same final row set
- if a valid teacher answer exists, the final row should not silently degrade to
  `missing_answer`
- a course may legitimately render zero final rows if no valid learner-facing
  outputs survive

### 7. Shared Artifact Rendering

Purpose:

- write run-scoped canonical JSONL artifacts under
  `data/pipeline_runs/<run_id>/`
- preserve enough stage outputs for inspection and debugging
- keep one canonical artifact family per stage result

Canonical run-scoped families:

- normalized course artifacts
- semantic extraction artifacts
- reviewed question artifacts
- reviewed synthetic-answer artifacts
- final row artifacts

### 8. Per-Course YAML Rendering

Purpose:

- write one course bundle per processed course
- preserve normalized input, semantic outputs, review outcomes, final rows, and
  summary counters

The per-course YAML is an inspection surface, not an independent source of
truth.

It must be rendered from the same canonical row set as shared outputs.

### 9. Run Summary Rebuild

Purpose:

- rebuild `run_summary.yaml` from the merged shared artifact state after upsert
- not from detached counters or stale intermediate assumptions

The run summary must report:

- course-level row counts
- answered/rejected/errored counts
- artifact row counts
- synthetic answer counts
- quality metrics
- teacher-answer propagation metrics
- LLM call, token, and cost metrics when logs are available

The summary must include zero-row processed courses when they have a rendered
bundle.

### 10. Publish

Purpose:

- merge run outputs into `data/final`
- preserve non-overlapping courses
- overwrite only affected courses by `course_id`

Publish rules:

- publish only after all selected courses reach a terminal course-level outcome
- publish only if rendered outputs pass consistency checks
- rebuild `data/final/run_summary.yaml` from published shared artifacts
- propagate publish-scoped `logs/llm_calls.jsonl` and `logs/pricing_snapshot.json`
  so published summaries can retain LLM observability

### 11. Inspection Bundle

Purpose:

- create a stable filtered inspection bundle from `data/final`
- support human review and diffable snapshots

Bundle rules:

- build one canonical bundle selection object first
- filter canonical shared artifacts only from that shared selection
- copy selected `course_yaml/<course_id>.yaml` files
- emit a manifest with selection metadata, counts, and published-run metadata
- emit `bundle_validation.json` with expected vs observed ids and row counts
- fail if required selected course outputs are missing
- fail if bundle validation does not pass

## Storage Model

Run directory:

```text
data/pipeline_runs/<run_id>/
  excluded_courses.jsonl
  normalized_courses.jsonl
  course_context_frames.jsonl
  question_context_frames.jsonl
  train_rows.jsonl
  cache_rows.jsonl
  semantic_topics.jsonl
  semantic_correlated_topics.jsonl
  semantic_topic_questions.jsonl
  semantic_correlated_topic_questions.jsonl
  semantic_synthetic_answers.jsonl
  semantic_review_decisions.jsonl
  answers.jsonl
  all_rows.jsonl
  run_summary.yaml
  logs/
    pipeline.log
    llm_calls.jsonl
    pricing_snapshot.json
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
  course_context_frames.jsonl
  question_context_frames.jsonl
  train_rows.jsonl
  cache_rows.jsonl
  semantic_topics.jsonl
  semantic_correlated_topics.jsonl
  semantic_topic_questions.jsonl
  semantic_correlated_topic_questions.jsonl
  semantic_synthetic_answers.jsonl
  semantic_review_decisions.jsonl
  answers.jsonl
  all_rows.jsonl
  run_summary.yaml
  logs/
    llm_calls.jsonl
    pricing_snapshot.json
  course_yaml/
    <course_id>.yaml
```

Filtered bundle directory:

```text
/tmp/inspectgion_bundl_<bundle_id>/
  normalized_courses.jsonl
  course_context_frames.jsonl
  question_context_frames.jsonl
  train_rows.jsonl
  cache_rows.jsonl
  semantic_topics.jsonl
  semantic_correlated_topics.jsonl
  semantic_topic_questions.jsonl
  semantic_correlated_topic_questions.jsonl
  semantic_synthetic_answers.jsonl
  semantic_review_decisions.jsonl
  answers.jsonl
  all_rows.jsonl
  run_summary.yaml
  source_run_summary.yaml
  pipeline_run_manifest.yaml
  bundle_validation.json
  inspectgion_bundle.log
  course_yaml/
    <course_id>.yaml
```

Important rule:

- exact file names may still be refined in code
- what matters is one canonical family per stage result and no obsolete
  duplicate projections kept alive only for stale consumers

## Incremental Writes and Upserts

The file-first model must support overlap-safe reruns.

For shared JSONL artifacts:

- identify affected `course_id`s in the current slice
- remove prior rows for those `course_id`s
- append the fresh rows for those same `course_id`s
- preserve all other rows

For per-course YAML:

- rewrite only affected `course_yaml/<course_id>.yaml`

For summaries:

- compute summary values from the merged shared artifact state after upsert

## Consistency Checks

The pipeline must fail fast if rendered outputs diverge.

Required reconciliation checks:

- course presence parity between shared outputs and per-course YAML
- final row count parity by course
- answered row count parity by course
- answer count parity by course
- shared answer row count equals answered final-row count where expected
- no final published answer row uses grounded brochure-span answer mode

These checks must run before publish and during summary rebuild.

## Logging

Logging remains a first-class operational artifact.

Per-run logging must include:

- pipeline lifecycle events
- per-stage start/completion/duration
- row counts by stage
- LLM model identifiers and request ids
- warnings and failures
- upsert decisions
- publish actions
- inspection-bundle actions

Required structured logs:

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

## Disallowed Architecture

The following are explicitly out of bounds for V1:

- grounded brochure-span answer generation in the main flow
- deterministic topic extraction as the canonical semantic source
- deterministic correlated-topic discovery as the canonical semantic source
- deterministic question generation as the canonical semantic source
- shared outputs derived from a different row set than per-course YAML
- obsolete artifact aliases kept alive only for dead consumers

## Migration Guidance

During the reshape:

- use `docs/codex_full_spec_llm_semantic_pipeline.md` as the canonical semantic
  policy reference
- use this document as the detailed architecture target
- use `docs/ACCEPTANCE_CRITERIA.md` for completion gates
- use `docs/CODEX_TASK.md` for implementation direction
- use `docs/DELETE_LIST.md` for removal pressure
- use `docs/TEST_PLAN.md` for regression coverage requirements
- keep historical planning material under `docs/sunset/`
