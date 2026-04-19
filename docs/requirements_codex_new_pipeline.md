# Requirements for Codex: Vetted-Topic Course Q/A Pipeline

## Purpose

Build a new clean-sheet pipeline that turns scraped course metadata into a
small, inspectable set of learner-facing question/answer artifacts.

The current redesign should follow this principle:

1. extract many candidate topics
2. dedupe and canonicalize them into unique topics
3. vet topics before question generation
4. generate only simple single-topic questions from vetted topics
5. generate multi-topic questions only for vetted related pairs
6. answer only when supporting evidence exists

The system must prefer fewer, stronger artifacts over high-volume weak output.

## Context

- Scraped input data already exists under `datacamp_data/`
- The project should be built for Codex to work on directly in the selected
  repository directory
- Codex should be able to inspect files, edit code, and run commands locally
- The implementation should favor clear project structure and explicit tests

## Product goal

Given a scraped course record, produce final rows shaped like:

`<course, [relevant_topics], question_text, question_answer, correctness>`

Where:

- `course` identifies the normalized course
- `relevant_topics` is a list of canonical topic labels
- `question_text` is the final validated question
- `question_answer` is a short evidence-grounded answer
- `correctness` is one of:
  - `correct`
  - `incorrect`
  - `uncertain`

## Non-goals

The first version should not attempt to build:

- adaptive tutoring
- open-domain answering
- speculative serving
- student-state personalization
- ontology-heavy knowledge graphs
- unconstrained comparison generation
- large-scale paraphrase expansion

## Core design principles

- Prefer atomic topics over chapter headings
- Prefer rejection over unsupported invention
- Prefer explicit evidence spans over inferred answers
- Prefer simple learner questions over clever question generation
- Prefer typed stages and structured artifacts over monolithic prompts
- Prefer batch-friendly stages that are easy to rerun independently
- Never silently drop failures

## Required architecture

The pipeline must use:

- Python 3.11+
- Prefect for orchestration
- Pydantic v2 for schemas
- JSONL for stage artifacts
- YAML for per-course inspection bundles
- file-first storage under `data/pipeline_runs/<run_id>/`

## High-level pipeline

```text
scraped course files
-> normalization
-> raw topic extraction
-> canonicalization / dedupe
-> related-topic discovery
-> topic vetting
-> single-topic question generation
-> pairwise question generation
-> question validation / repair / rejection
-> answer generation with evidence
-> final ledger rows
-> per-course YAML bundle
-> run summary
```

## Required stages

### Stage 0: Normalize course records

#### Goal

Convert raw scraped records into a stable `NormalizedCourse` object.

#### Input

Files under `datacamp_data/`.

#### Required fields in normalized output

```yaml
course_id: "24416"
title: "Cleaning Data in R"
provider: "DataCamp"
summary: "..."
overview: "..."
chapters:
  - chapter_index: 1
    title: "Common Data Problems"
    summary: "..."
    source: "syllabus"
metadata:
  level: "Intermediate"
  duration_hours: 4.0
source_refs:
  title: true
  summary: true
  overview: true
  syllabus: true
```

#### Rules

- Preserve original text needed for evidence
- Recover chapters from syllabus when present
- Infer chapters from overview only when needed
- Exclude clearly corrupted records into `excluded_courses.jsonl`
- Do not let malformed title fragments pass as valid titles

#### Required output artifact

- `normalized_courses.jsonl`
- `excluded_courses.jsonl`

---

### Stage 1: Extract raw candidate topics

#### Goal

Extract many candidate learner-facing topics from course text.

#### Source fields

- title
- summary
- overview
- chapter titles
- chapter summaries

#### Required topic categories at extraction time

- concept
- procedure
- tool
- method
- metric
- test
- comparison_pair_candidate
- wrapper_or_container_candidate
- unknown

#### Rules

- Be permissive in this stage
- Extract topics with evidence spans
- Record source field and confidence
- Split coordinated labels like `X and Y` only when both sides are supported
- Keep chapter-heading-only topics marked as low-trust candidates

#### Required schema

```yaml
course_id: "24416"
candidate_topics:
  - topic_id: "t_001"
    raw_label: "categorical data"
    normalized_label: "categorical data"
    provisional_type: "concept"
    evidence_spans:
      - source: "chapter_summary"
        text: "Categorical and text data can often be some of the messiest..."
    confidence: 0.91
```

#### Required artifact

- `topics.jsonl`

---

### Stage 2: Canonicalize into unique topics

#### Goal

Merge duplicates and alias variants into unique canonical topics.

#### Examples

- `ARIMA`
- `ARIMA model`
- `ARIMA models`

should collapse into one canonical topic.

#### Rules

- Normalize case and punctuation
- Preserve display label separately from normalized label
- Track aliases
- Keep all supporting evidence spans
- Do not collapse unrelated chapter wrappers into real concepts

#### Required schema

```yaml
course_id: "24416"
canonical_topics:
  - canonical_topic_id: "ct_001"
    canonical_label: "categorical data"
    aliases:
      - "categorical data"
    primary_type: "concept"
    evidence_spans:
      - source: "chapter_summary"
        text: "Categorical and text data can often be some of the messiest..."
    member_topic_ids:
      - "t_001"
```

#### Required artifact

- `canonical_topics.jsonl`

---

### Stage 3: Discover related topic pairs

#### Goal

Build a small set of evidence-backed related topic pairs.

#### Important note

Use the term `related topics`, not raw `correlated topics`, unless correlation
is explicitly computed and justified.

#### Allowed reasons for relation

- explicit comparison phrase in source text
- shared chapter summary with clear paired framing
- prerequisite / dependency wording
- shared method family with explicit evidence
- lexical / semantic closeness plus shared local evidence

#### Disallowed relation logic

- do not relate two topics by embedding similarity alone
- do not pair real topics with wrapper/container topics
- do not create all-pairs comparisons inside a course

#### Required schema

```yaml
course_id: "24416"
related_topic_pairs:
  - pair_id: "p_001"
    topic_x: "categorical data"
    topic_y: "text data"
    relation_type: "paired_scope"
    evidence_spans:
      - source: "chapter_title"
        text: "Categorical and Text Data"
      - source: "chapter_summary"
        text: "...category labels... and strings..."
    confidence: 0.82
```

#### Required artifact

- `related_topic_pairs.jsonl`

---

### Stage 4: Vet topics and related pairs

#### Goal

Filter canonical topics into usable learner-facing units before generating
questions.

#### Output classes for topics

- `keep`
- `keep_entry_only`
- `keep_no_pairwise`
- `reject`

#### Output classes for pairs

- `keep_pair`
- `reject_pair`

#### Required topic rules

Always reject or heavily suppress normalized labels like:

- `case study`
- `overview`
- `introduction`
- `putting it all together`
- `summary`
- `conclusion`

unless the surrounding evidence clearly turns them into a genuine concept.

Wrapper/container types must not behave like normal concepts.

#### Required pair rules

A pair may be kept only if:

- both topics are individually kept
- neither topic is a wrapper/container
- there is explicit relation evidence

#### Required outputs

```yaml
topic_decisions:
  - canonical_topic_id: "ct_001"
    canonical_label: "categorical data"
    decision: "keep"
    allow_single_topic_questions: true
    allow_pairwise_questions: true
    reason: "strong_atomic_concept"

pair_decisions:
  - pair_id: "p_001"
    decision: "keep_pair"
    reason: "paired_scope_supported"
```

#### Required artifacts

- `vetted_topics.jsonl`
- `vetted_topic_pairs.jsonl`

---

### Stage 5: Generate simple single-topic questions

#### Goal

Generate trivial, high-confidence learner questions from vetted topics.

#### Rule

This is the default generation path and should produce the majority of useful
rows.

#### Allowed question families by topic type

##### concept

- `entry`
- `purpose`
- `example`

##### procedure / method / tool

- `entry`
- `procedure`
- `purpose`
- `failure`

##### metric / test

- `entry`
- `interpretation`
- `purpose`

##### wrapper/container

- none by default

#### Core simple patterns

For concept-like topics `X`:

- What is X?
- What does X mean?
- Why does X matter?
- What is a simple example of X?

For procedure / tool / method topics `X`:

- What is X?
- How do you use X?
- When would you use X?
- What can go wrong with X?

For metric / test topics `X`:

- What is X?
- What does X tell us?
- How do you interpret X?

#### Rules

- Use only patterns allowed by topic type
- Do not force all patterns on all topics
- Do not generate from rejected or wrapper topics
- Attach source topic ids and pattern metadata

#### Required artifact

- `single_topic_questions.jsonl`

---

### Stage 6: Generate multi-topic questions from vetted pairs

#### Goal

Generate pairwise questions only for evidence-backed kept pairs.

#### Allowed patterns

For pair `(X, Y)`:

- How is X different from Y?
- How are X and Y related?
- When would you use X instead of Y?
- What are the tradeoffs between X and Y?

#### Disallowed default pattern

Do not generate `How is X better than Y?` unless the source text explicitly
frames superiority or preference.

#### Rules

- No pairwise generation without `keep_pair`
- No pairwise generation involving rejected topics
- Attach pair evidence spans

#### Required artifact

- `pairwise_questions.jsonl`

---

### Stage 7: Validate, repair, or reject questions

#### Goal

For each generated question, either:

- accept it
- repair it locally
- reject it explicitly

#### Allowed local repairs

- punctuation cleanup
- article cleanup
- plurality cleanup
- minor wording cleanup that preserves exact intent

#### Disallowed repairs

- changing question family
- changing semantic intent
- turning valid syntax into invalid syntax
- converting one grammatical structure into another risky structure

#### Required reject reasons

- `unsupported_topic`
- `broad_heading`
- `compound_topic`
- `invalid_pair`
- `duplicate_intent`
- `malformed`
- `unnatural`
- `thin_answer`

#### Example

Bad:
- `Why does strings?`

Expected behavior:
- reject as `malformed` or `unnatural`
- never keep as repaired

#### Required artifact

- `question_validation.jsonl`

---

### Stage 8: Answer only validated questions with evidence

#### Goal

Generate short answers only for accepted questions that have supporting spans.

#### Hard rules

- No answer row without at least one supporting evidence span
- Empty evidence arrays are not allowed on answered rows
- Generic fallback text must not be used as a normal answer mode
- If evidence is weak, mark `uncertain`
- If evidence is absent, reject earlier or mark unsupported before answering

#### Required answer style

- short
- direct
- evidence-grounded
- no invented details

#### Required correctness labels

- `correct`
- `incorrect`
- `uncertain`

#### Required artifact

- `answers.jsonl`

---

### Stage 9: Build final ledger rows

#### Goal

Persist one authoritative terminal row per generated question.

#### Invariant

Every generated question must end in one terminal state:

- answered
- rejected
- errored

No silent disappearance.

#### Required final schema

```yaml
row_id: "r_000001"
course:
  course_id: "24416"
  title: "Cleaning Data in R"
relevant_topics:
  - "categorical data"
question_text: "What is categorical data?"
question_family: "entry"
question_answer: "Categorical data is data represented by labels or
  categories rather than free-form numeric values."
correctness: "correct"
status: "answered"
reject_reason: null
source_evidence:
  - source: "chapter_summary"
    text: "Categorical and text data can often be some of the messiest..."
```

#### Required artifact

- `all_rows.jsonl`

---

### Stage 10: Render per-course YAML bundle and run summary

#### Goal

Produce a human-inspectable bundle for every course and a QA summary for the
run.

#### Per-course YAML must include

- normalized course
- raw topics
- canonical topics
- vetted topics
- related topic pairs
- single-topic questions
- pairwise questions
- validation decisions
- answers
- final rows
- summary counts

#### Required run summary metrics

- course_count
- excluded_course_count
- total_raw_topics
- total_canonical_topics
- total_vetted_topics
- total_related_pairs
- total_single_topic_questions
- total_pairwise_questions
- accepted_question_count
- rejected_question_count
- errored_question_count
- answered_count
- correct_count
- incorrect_count
- uncertain_count
- heading_like_topic_rate
- answer_rows_without_evidence_count
- malformed_repair_count

#### Required artifacts

- `course_yaml/<course_id>.yaml`
- `run_summary.yaml`

## Prompting requirements

Use multiple prompts, not one giant prompt.

### Prompt A: raw topic extraction

Input:
- title
- summary
- overview
- chapter titles and summaries

Output:
- raw topics with evidence and provisional type

### Prompt B: topic vetting / typing confirmation

Input:
- canonical topics
- evidence spans
- related local context

Output:
- keep / reject decision
- final topic type
- pairwise eligibility

### Prompt C: question generation

Input:
- vetted topic or vetted pair
- allowed pattern families

Output:
- candidate questions with family metadata

### Prompt D: validation / repair / reject

Input:
- candidate question
- source topic(s)
- evidence spans

Output:
- accepted / repaired / rejected
- final question if repaired
- reject reason if rejected

### Prompt E: answer generation

Input:
- accepted question
- source evidence spans

Output:
- answer text
- correctness label
- evidence references

## Model guidance

Keep model selection centralized in config.

### Strong reasoning model

Use for:
- topic extraction from noisy course text
- topic vetting
- repair / reject decisions
- answer generation with correctness labeling

### Smaller cheaper model

Use for:
- question expansion from vetted topics
- deterministic pattern-conditioned generation

### Important design note

Question generation should be low-cost and constrained.
The expensive reasoning should happen in topic vetting and validation.

## Prefect requirements

### Main flow

`course_question_pipeline_flow`

### Required tasks

1. `load_course_files`
2. `normalize_course_record`
3. `extract_raw_topics`
4. `canonicalize_topics`
5. `discover_related_pairs`
6. `vet_topics`
7. `generate_single_topic_questions`
8. `generate_pairwise_questions`
9. `validate_questions`
10. `answer_questions`
11. `build_final_rows`
12. `render_course_bundle`
13. `render_run_summary`

### Flow behavior

- one mapped unit per course
- stage artifacts persisted after every step
- rerunnable from intermediate artifacts
- retries only for transient failures

## Required repo structure

```text
project/
  src/
    course_pipeline/
      flows/
      tasks/
      prompts/
      schemas/
      utils/
      writers/
      config/
  tests/
    fixtures/
    regression/
  docs/
  data/
    pipeline_runs/
```

## Required tests

At minimum include fixtures and tests for:

1. malformed-title exclusion
2. coordinated split success case
3. wrapper-topic rejection case
4. valid related-pair case
5. invalid related-pair blocking case
6. malformed repair prevention
7. answer-with-evidence requirement
8. no answered row with empty evidence

### Must-have regression examples

- `Categorical and Text Data` splits into:
  - `categorical data`
  - `text data`
- `case study` does not become a canonical learner topic
- `putting it all together` does not become a canonical learner topic
- `How is X different from case study?` cannot be generated
- `Why do we use X?` can never degrade into `Why does X?`

## Required acceptance thresholds

The first full-corpus rerun is acceptable only if all of these hold:

- heading-like canonical topics `< 5%`
- answered rows without evidence `= 0`
- malformed repaired questions `= 0`
- rejected question count `> 0`
- excluded corrupted course count is plausible and nonzero when corruption
  exists
- pairwise questions must always carry explicit pair evidence
- fallback generic-answer rate `< 10%`
- every strong vetted topic has at least one valid single-topic entry question

## Required outputs

The pipeline must emit these files:

- `normalized_courses.jsonl`
- `excluded_courses.jsonl`
- `topics.jsonl`
- `canonical_topics.jsonl`
- `related_topic_pairs.jsonl`
- `vetted_topics.jsonl`
- `vetted_topic_pairs.jsonl`
- `single_topic_questions.jsonl`
- `pairwise_questions.jsonl`
- `question_validation.jsonl`
- `answers.jsonl`
- `all_rows.jsonl`
- `run_summary.yaml`
- `course_yaml/<course_id>.yaml`

## What Codex should do first

1. inspect `datacamp_data/`
2. propose a concrete repo tree
3. implement schemas and artifact writers
4. implement normalization and exclusion
5. implement topic extraction and canonicalization
6. implement vetting before any answer logic
7. implement single-topic questions before pairwise questions
8. add regression fixtures
9. only then implement answer generation

## Final instruction to Codex

Do not optimize for volume.

Optimize for:
- fewer topics
- better topics
- simpler questions
- explicit evidence
- meaningful rejections
- reproducible artifacts

If a design choice is ambiguous, prefer:
- earlier filtering
- simpler learner questions
- smaller trusted output sets
- topic vetting before question generation
# Historical Note

This requirements note predates the hard migration to synthetic tutor answers.
Where it describes evidence-grounded final answers as the default runtime, the
current implementation should be considered authoritative instead.
