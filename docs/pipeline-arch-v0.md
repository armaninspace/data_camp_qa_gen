# Pipeline Architecture V0

## Purpose

This document describes the current `course_pipeline` architecture as it
exists in the repo today.

It is a V0 architecture note, not a frozen specification. The goal is to make
the current pipeline easy to reason about, debug, and modify.

The pipeline turns scraped course metadata into:

- machine-readable stage artifacts in JSONL
- per-course YAML inspection bundles
- merged published outputs in `data/final`
- optional inspection bundles filtered from published outputs

The current implementation is deliberately conservative:

- preflight excludes clearly bad inputs
- topic extraction is mostly deterministic
- question generation is bounded and currently entry-first
- pairwise questions are heavily gated
- answers require evidence spans
- publish is overlap-safe by `course_id`

## Repo Components

Main package layout:

```text
src/course_pipeline/
  cli.py
  config.py
  llm.py
  pattern_bank.py
  schemas.py
  run_logging.py
  flows/
    course_question_pipeline.py
  tasks/
    normalize.py
    preflight_validate.py
    extract_topics.py
    canonicalize.py
    discover_related_pairs.py
    vet_topics.py
    generate_questions.py
    repair_questions.py
    answer_questions.py
    build_ledger.py
    render.py
  prompts/
    extract_topics.md
    generate_questions.md
    repair_or_reject.md
    answer_questions.md
```

## Design Principles

The implementation currently follows these high-level rules:

- file-first artifacts over hidden state
- deterministic ordering for slice selection
- `course_id` as the merge and upsert key
- bounded question generation instead of open-ended generation
- evidence-bound answers only
- preserve enough artifacts to debug each stage

## End-to-End Flow

Top-level flow:

- function: [course_question_pipeline_flow](/code/src/course_pipeline/flows/course_question_pipeline.py)

Stages:

1. load course paths
2. preflight validate selected paths
3. normalize course
4. extract atomic topics
5. canonicalize topics
6. discover related pairs
7. vet topics and pairs
8. generate single-topic questions
9. generate pairwise questions
10. validate questions
11. answer questions
12. build ledger rows
13. persist stage artifacts
14. rebuild run summary
15. publish final outputs

Post-publish utility job:

- `mk_inspectgion_bundle`

## High-Level Data Model

Key schema objects are defined in [schemas.py](/code/src/course_pipeline/schemas.py).

Important records:

- `NormalizedCourse`
- `Topic`
- `CanonicalTopic`
- `RelatedTopicPair`
- `VettedTopic`
- `VettedTopicPair`
- `GeneratedQuestion`
- `QuestionValidationRecord`
- `QuestionRepair`
- `AnswerRecord`
- `LedgerRow`
- `CourseBundle`
- `PreflightCourseDecision`

Relationship sketch:

```text
raw course
  -> NormalizedCourse
  -> Topic*
  -> CanonicalTopic*
  -> RelatedTopicPair*
  -> VettedTopic*
  -> VettedTopicPair*
  -> GeneratedQuestion*
  -> QuestionValidationRecord*
  -> QuestionRepair*
  -> AnswerRecord*
  -> LedgerRow*
  -> CourseBundle
```

## Stage-by-Stage Description

### 0. Preflight Validation

Code:

- [preflight_validate.py](/code/src/course_pipeline/tasks/preflight_validate.py)

Input:

- raw scraped course dict

Output:

- `PreflightCourseDecision`

Purpose:

- reject malformed titles
- reject courses with no usable overview and no syllabus
- reject overview-only low-quality marketing-heavy sources

Current exclusion reasons:

- `malformed_title`
- `no_usable_content`
- `low_quality_source`

Current quality states:

- `usable`
- `partial`
- `broken`

Current behavior:

- `broken` courses are written to `excluded_courses.jsonl`
- only `usable` and `partial` proceed into the main pipeline

### 1. Normalize Course

Code:

- [normalize.py](/code/src/course_pipeline/tasks/normalize.py)

Purpose:

- coerce raw scraped records into `NormalizedCourse`
- normalize title and `course_id`
- preserve summary, overview, chapters, metadata, and source refs

Chapter behavior:

- if `syllabus` exists, use it directly
- otherwise infer chapter-like headings only from overview paragraphs that look
  like short headings

Important point:

- overview inference is intentionally limited now; it no longer treats arbitrary
  wrapped prose lines as headings

### 2. Extract Atomic Topics

Code:

- [extract_topics.py](/code/src/course_pipeline/tasks/extract_topics.py)

Purpose:

- generate first-pass atomic topics from chapter titles, chapter summaries, and
  overview lexical hits

Current extraction sources:

- chapter titles
- chapter summaries
- overview text
- summary text

Current extraction mechanisms:

- coordinated phrase split
- comma bundle split
- lexical pattern extraction from summaries
- lexical topic scanning in overview text

Current normalization in extraction:

- lowercase cleanup
- whitespace cleanup
- split `X and Y`
- split `X & Y`
- split comma-joined labels like `logic, control flow, loops`
- singularize small obvious plurals such as `loops -> loop`,
  `dictionaries -> dictionary`

Current heading/filter pressure:

- explicit always-reject topic labels
- heading-like prefixes such as:
  - `introduction to ...`
  - `creating ...`
  - `manipulating ...`
  - `putting it all together`
  - `case study`

### 3. Canonicalize Topics

Code:

- [canonicalize.py](/code/src/course_pipeline/tasks/canonicalize.py)

Purpose:

- merge exact or near-exact normalized topic variants into canonical topics

Current canonicalization is intentionally simple:

- lowercase
- trim
- remove leading `the`
- collapse whitespace
- singularize a trailing `models -> model`

It is still weak compared with the desired future state. It mainly removes
literal duplicates, not semantic duplicates.

### 4. Discover Related Pairs

Code:

- [discover_related_pairs.py](/code/src/course_pipeline/tasks/discover_related_pairs.py)

Purpose:

- discover candidate topic pairs worth comparing

Current pair discovery requires evidence:

- same evidence span mentioning both topics
- coordinated phrasing like `x and y`
- explicit comparison language like `compare`, `versus`, `instead of`

Current relation types:

- `paired_scope`
- `explicit_comparison`
- `shared_local_evidence`

Only the stronger relation types are useful downstream.

### 5. Vet Topics and Pairs

Code:

- [vet_topics.py](/code/src/course_pipeline/tasks/vet_topics.py)

Purpose:

- decide what is allowed to move forward

Topic vetting currently combines:

- wrapper/heading rejection
- lightweight topic quality classification
- pairwise-eligibility control

Current lightweight topic-quality labels are represented in `reason` values and
internal classification outcomes:

- `good_atomic_topic`
- `chapter_wrapper`
- `sentence_fragment`
- `marketing_claim`
- `course_preamble`
- `too_broad`

Current topic decisions:

- `keep`
- `keep_entry_only`
- `keep_no_pairwise`
- `reject`

Current pair policy:

- keep only if both topics survived vetting
- keep only if both topics allow pairwise generation
- keep only if relation type is strong
- reject weak `shared_local_evidence`

### 6. Generate Questions

Code:

- [generate_questions.py](/code/src/course_pipeline/tasks/generate_questions.py)
- [pattern_bank.py](/code/src/course_pipeline/pattern_bank.py)

Current question generation is intentionally narrow.

Single-topic generation:

- currently emits only `entry` questions
- shape: `What is {x}?`

Pairwise generation:

- only for vetted pairs
- only for strong pair relation types
- currently effectively suppressed unless evidence is very strong

This is deliberate. The current bottleneck is source quality and topic
normalization, not broad question coverage.

### 7. Validate Questions

Code:

- [repair_questions.py](/code/src/course_pipeline/tasks/repair_questions.py)

Purpose:

- reject broad or malformed generated questions
- dedupe question intent

Current checks:

- broad-heading rejection
- compound topic rejection
- malformed wording rejection
- duplicate intent rejection

Output:

- `QuestionValidationRecord`

Note:

- the code path is now closer to “accept or reject” than to a rich repair
  system, even though `QuestionRepair` remains in the compatibility layer

### 8. Answer Questions

Code:

- [answer_questions.py](/code/src/course_pipeline/tasks/answer_questions.py)

Purpose:

- answer only from support spans derived from the course text

Current evidence strategy:

- split summary, overview, chapter titles, and chapter summaries into spans
- match topic labels against those spans
- require evidence before returning an answer

Correctness labels:

- `correct`
- `incorrect`
- `uncertain`

Current answer pressure:

- weak evidence becomes `uncertain`
- no evidence means no answer row is created
- ledger then records a terminal `errored` row if an accepted question has no
  answer

### 9. Build Ledger Rows

Code:

- [build_ledger.py](/code/src/course_pipeline/tasks/build_ledger.py)

Purpose:

- create the terminal learner-facing row representation

Row statuses:

- `answered`
- `rejected`
- `errored`

This ledger is the main downstream contract for “what happened to each
question.”

### 10. Persist Artifacts and Publish

Code:

- [render.py](/code/src/course_pipeline/tasks/render.py)

Purpose:

- write per-stage JSONL artifacts
- write per-course YAML bundles
- rebuild merged run summaries
- publish overlap-safe final outputs to `data/final`

Important behavior:

- JSONL artifacts upsert by `course_id`
- per-course YAML rewrites only affected course files
- shared outputs are rebuilt from the merged state after upsert

## Prompt Families

The repo includes four prompt files:

- [extract_topics.md](/code/src/course_pipeline/prompts/extract_topics.md)
- [generate_questions.md](/code/src/course_pipeline/prompts/generate_questions.md)
- [repair_or_reject.md](/code/src/course_pipeline/prompts/repair_or_reject.md)
- [answer_questions.md](/code/src/course_pipeline/prompts/answer_questions.md)

These are the intended prompt families:

1. topic extraction
2. question generation
3. repair-or-reject
4. answer generation

Current status:

- the prompt files exist
- the OpenAI adapter exists
- the current runtime path is still mostly deterministic
- the prompts are scaffolding for the next generation of the pipeline

### Prompt: Extract Topics

File:

- [extract_topics.md](/code/src/course_pipeline/prompts/extract_topics.md)

Intent:

- extract learner-facing atomic topics
- prefer concepts, procedures, tools, metrics, tests
- split coordinated labels when justified
- reject vague headings

Expected output shape:

- structured JSON object

### Prompt: Generate Questions

File:

- [generate_questions.md](/code/src/course_pipeline/prompts/generate_questions.md)

Intent:

- map canonical topics to bounded question families
- avoid forcing every family on every topic
- allow comparisons only for plausible topic pairs

Expected output shape:

- structured JSON object

### Prompt: Repair or Reject

File:

- [repair_or_reject.md](/code/src/course_pipeline/prompts/repair_or_reject.md)

Intent:

- accept
- repair slightly
- or reject

Allowed repairs:

- grammar
- article cleanup
- plurality cleanup
- wording nudge

Expected output shape:

- structured JSON object

### Prompt: Answer Questions

File:

- [answer_questions.md](/code/src/course_pipeline/prompts/answer_questions.md)

Intent:

- answer only from course evidence
- keep answers short
- use `uncertain` when support is weak

Expected output shape:

- structured JSON object

## LLM Adapter

Code:

- [llm.py](/code/src/course_pipeline/llm.py)
- [config.py](/code/src/course_pipeline/config.py)

Current adapter behavior:

- thin wrapper around the OpenAI Responses API
- `responses.parse(...)`
- expects a JSON object result
- model choice is driven by env-configured settings

Configured model slots:

- `OPENAI_MODEL_EXTRACT`
- `OPENAI_MODEL_GENERATE`
- `OPENAI_MODEL_REPAIR`
- `OPENAI_MODEL_ANSWER`

Current reality:

- these model settings are configured and logged
- but the deterministic pipeline still does most of the work today

## Logging

Code:

- [run_logging.py](/code/src/course_pipeline/run_logging.py)

Log files under each run:

- `logs/pipeline.log`
- `logs/llm_calls.jsonl`
- `logs/stage_metrics.jsonl`
- `logs/publish.log`
- `logs/inspectgion_bundle.log`

Structured stage metrics fields:

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

Structured LLM call fields:

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

## Artifacts

Run-scoped artifacts under `data/pipeline_runs/<run_id>/`:

- `excluded_courses.jsonl`
- `normalized_courses.jsonl`
- `topics.jsonl`
- `canonical_topics.jsonl`
- `related_topic_pairs.jsonl`
- `vetted_topics.jsonl`
- `vetted_topic_pairs.jsonl`
- `single_topic_questions.jsonl`
- `pairwise_questions.jsonl`
- `question_validation.jsonl`
- `question_candidates.jsonl`
- `question_repairs.jsonl`
- `answers.jsonl`
- `all_rows.jsonl`
- `run_summary.yaml`
- `course_yaml/<course_id>.yaml`

Published artifacts under `data/final/`:

- same merged shared artifacts except `excluded_courses.jsonl`
- merged `course_yaml/<course_id>.yaml`
- merged `run_summary.yaml`

Inspection bundle output:

- `tmp/inspectgion_bundl_<bundle_id>/...`

## Current Pseudocode

### Main Run

```text
function run_pipeline(input_dir, output_dir, final_dir, slice_start, slice_end, publish):
    logger = RunLogger(output_dir)
    logger.ensure_files()

    selected_paths = load_course_paths(input_dir, slice_start, slice_end)
    preflight = preflight_validate_selected_paths(selected_paths)
    write excluded_courses.jsonl

    for each runnable course path:
        raw = load_raw_course(path)
        course = normalize_course_record(raw)

        topics = extract_atomic_topics_baseline(course)
        canonical_topics = canonicalize_topics(topics)
        related_pairs = discover_related_pairs(canonical_topics)
        vetted_topics, vetted_pairs = vet_topics_and_pairs(canonical_topics, related_pairs)

        kept_topics = vetted_topics where decision != reject
        kept_pairs = vetted_pairs where decision == keep_pair

        single_topic_questions = generate_single_topic_questions(kept_topics)
        pairwise_questions = generate_pairwise_questions(kept_pairs) if kept_topics else []

        validations = validate_questions(single_topic_questions + pairwise_questions)
        candidates = compatibility_projection(validations.source_questions)
        repairs = compatibility_projection(validations)
        answers = answer_questions(course, canonical_topics, repairs)
        rows = build_ledger_rows(course, candidates, repairs, answers)

        persist_stage_artifacts(...)

    run_summary = rebuild_run_summary(output_dir)

    if no excluded courses and no rejected questions:
        fail run with rejection-pressure error

    if publish:
        publish_final_outputs(output_dir, final_dir)
```

### Preflight

```text
function preflight_validate_course(raw):
    if title missing or junk:
        return broken(malformed_title)

    if no overview and no syllabus:
        return broken(no_usable_content)

    if syllabus empty and overview is marketing-heavy fragment soup:
        return broken(low_quality_source)

    if overview and syllabus:
        return usable

    return partial
```

### Topic Extraction

```text
function extract_atomic_topics_baseline(course):
    topics = []

    for chapter in course.chapters:
        heading = normalize(chapter.title)

        if heading is coordinated or comma-joined:
            split into subtopics
        else if heading is not heading-like:
            add heading as topic

        scan chapter summary for lexical patterns
        add matched atomic labels

    scan overview + summary for known lexical topics
    add them

    return deduped topics
```

### Vetting

```text
function vet_topics_and_pairs(canonical_topics, related_pairs):
    for each topic:
        if wrapper or heading-like:
            reject
        else if sentence fragment / marketing claim / too broad / course preamble:
            reject
        else if weak or unknown:
            keep entry only
        else:
            keep without pairwise by default

    for each pair:
        keep only if:
            both topics survived
            both allow pairwise
            evidence exists
            relation type is strong

    return vetted_topics, vetted_pairs
```

### Answering

```text
function answer_questions(course, repairs):
    support_spans = split course text into evidence spans

    for each accepted repair:
        matched_topics = topic labels mentioned in question
        evidence = first strong matching span
        if no evidence:
            skip answer
        else:
            classify correctness
            emit AnswerRecord
```

## Current Bottlenecks

The main current bottlenecks are not pairwise reasoning.

They are:

1. source-quality gating
2. overview-derived fragment suppression
3. topic normalization
4. better canonical collapse
5. stronger believable rejection pressure

The current architecture is intentionally being pushed toward:

- fewer topics
- fewer questions
- stronger evidence
- more explicit terminal states

## Near-Term Evolution

Likely next architectural steps:

1. improve preflight low-quality detection
2. improve canonicalization beyond literal normalization
3. replace deterministic extraction with structured LLM extraction
4. replace deterministic validate/repair with structured LLM validation
5. keep pairwise generation disabled or rare until single-topic quality is strong

## Summary

V0 pipeline architecture can be summarized as:

```text
scraped course
  -> preflight gate
  -> normalized course
  -> deterministic topic extraction
  -> simple canonicalization
  -> related-pair discovery
  -> topic/pair vetting
  -> entry-first question generation
  -> validation
  -> evidence-bound answering
  -> terminal ledger rows
  -> run artifacts
  -> merged publish
  -> optional inspection bundle
```

That is the current system.

It is not yet the final intended LLM-first architecture, but it now has the
right operational shape:

- explicit gates
- explicit artifacts
- explicit terminal row states
- explicit publish semantics
# Historical Note

This V0 architecture note is superseded by the current runtime. The primary
`run` flow now publishes synthetic tutor answers and no longer calls
`answer_questions.py`.
