# Clean-Sheet Pipeline Spec

> Superseded note: this document describes an older staged design with grounded
> extraction/answer assumptions. For current implementation work, use
> `AGENTS.md`, `codex_full_spec_llm_semantic_pipeline.md`,
> `pipeline-arch-v1.md`, and `ACCEPTANCE_CRITERIA.md` instead.

## Goal

Build a pipeline that turns scraped course metadata into grounded,
learner-facing question and answer artifacts.

Final row shape:

`<course, [relevant_topics], question_text, question_answer, correctness>`

## High-level flow

```text
raw course yaml/json
-> preflight quality classification
-> normalized course
-> atomic topics/entities X
-> question candidates Q from patterns P
-> repaired or rejected questions Q2
-> answers + correctness labels
-> authoritative ledger
-> per-course YAML bundle
-> run summary
-> publish final outputs
-> inspection bundle job
```

## Why multiple prompts

Use multiple prompts.

Recommended split:
- Prompt A: atomic topic extraction
- Prompt B: question generation from topics and patterns
- Prompt C: repair or reject
- Prompt D: answer and judge correctness

Reasons:
- easier debugging
- cleaner retries
- clearer metrics
- lower blast radius for failure

## Stage 1: Normalize course

Input:
- raw scraped YAML or JSON

Output:
- `NormalizedCourse`

Rules:
- preserve source text for evidence
- infer chapters from overview if syllabus is missing
- keep confidence on inferred chapter recovery
- never silently drop malformed fields

## Preflight validation

Every raw scraped course must first be classified for source quality.

Quality states:
- `usable`
- `partial`
- `broken`

Rules:
- exclude `broken` courses from the runnable course set
- write excluded records to `excluded_courses.jsonl`
- allow `partial` courses only when the remaining text still supports grounded
  extraction
- do not invent missing chapters, blurbs, or structure to rescue broken inputs

Required exclusion fields:
- `course_id`
- `source_path`
- `quality_status`
- `exclude_reason`
- `title_raw`
- `overview_present`
- `syllabus_count`

## Stage 2: Extract atomic topics

Goal:
- return learner-facing atomic topics, not just chapter headings

Prefer:
- concepts
- procedures
- tools
- metrics/tests
- failure points
- explicit comparison pairs

Reject or down-rank:
- vague headings
- admin labels
- broad coordinated phrases left unsplit

Special rule:
If a heading is `X and Y`, split when the supporting text treats them as
distinct ideas.

## Stage 3: Canonicalize topics

Goal:
- merge obvious duplicates
- normalize labels
- keep display label and normalized label separate

Embeddings are optional in v1.

## Stage 4: Expand question patterns

Use a bounded question pattern bank.

Families:
- entry
- purpose
- mechanism
- procedure
- decision
- comparison
- example
- failure
- interpretation
- prerequisite

Input:
- canonical topics
- topic types
- pattern bank
- topic relations when available

Rules:
- every strong topic gets at least one entry question
- not every family applies to every topic
- do not generate awkward questions from broad labels

## Stage 5: Repair or reject

For each candidate:
- accept
- repair slightly
- reject with explicit reason

Allowed repairs:
- grammar
- articles
- plurality
- natural wording nudge

Not allowed:
- introducing unsupported concepts
- changing the intent beyond a small nudge

Reject reasons:
- unsupported
- broad_heading
- compound_topic
- duplicate_intent
- malformed
- unnatural
- thin_answer

## Stage 6: Answer and rate correctness

For each accepted question:
- answer conservatively from course evidence
- rate `correct`, `incorrect`, or `uncertain`

If evidence is weak, prefer `uncertain`.

## Stage 7: Build ledger

Every generated question candidate must end in a terminal state.

Terminal states:
- answered
- rejected
- errored

No silent disappearance.

## Stage 8: Render per-course YAML bundle

Per-course YAML bundle contents:
- normalized course
- extracted topics
- canonical topics
- question candidates
- repairs/rejections
- answers
- final rows
- summary stats

## Stage 9: Render run summary

Run summary should include:
- merged course count
- per-course summary rows
- aggregate artifact counts when available
- aggregate reject and correctness counts when available

The inspection bundle is not part of the core 9 pipeline stages.
It is a separate post-publish job that reads from `data/final`.

## Incremental run semantics

The pipeline must support incremental slice runs against a shared output
directory.

Rules:
- course-scoped artifacts use `course_id` as the primary upsert key
- a rerun of a slice must overwrite only rows for overlapping `course_id`s
- non-overlapping rows already present in the output directory must be preserved
- per-course YAML bundles may be rewritten for affected `course_id`s only
- `run_summary.yaml` must reflect the merged state after upserts, not only the
  most recent slice
- slice boundaries must resolve against a stable deterministic corpus ordering
- the default corpus ordering is lexicographic by input file path
- input paths must be normalized relative to the chosen input root before
  ordering
- overlap is defined by the intersecting `course_id` set after slice expansion

Example:
- if one run writes courses in the first `0-10%` of the corpus
- and a later run writes courses in the `5-20%` range
- then only the intersecting `5-10%` course rows should be replaced
- rows for `0-5%` and `10-20%` should remain intact

## Published final outputs

In addition to transient per-run artifacts, the pipeline must publish final
workproducts to `data/final` after every complete successful run.

Rules:
- `data/pipeline_runs/<run_id>/` is the transient debugging and inspection area
- `data/final/` is the stable checked-in publication area
- `data/final/` must be updated only after a run completes successfully
- published outputs must reflect the merged post-upsert state, not only the
  latest slice
- publishing must overwrite only overlapping `course_id` data and preserve
  non-overlapping published data

Publish-success rules:
- publish is allowed only when every input course in the current run reaches a
  final course-level outcome
- publish is still allowed when some question rows are `rejected` or `errored`,
  as long as course artifacts were fully rendered and the run completed
- publish must be blocked when a selected course is missing its rendered bundle,
  when shared artifacts are incomplete, or when the run terminates before
  rendering finishes
- blocked publish attempts must be logged

Published files:
- `data/final/normalized_courses.jsonl`
- `data/final/topics.jsonl`
- `data/final/canonical_topics.jsonl`
- `data/final/question_candidates.jsonl`
- `data/final/question_repairs.jsonl`
- `data/final/answers.jsonl`
- `data/final/all_rows.jsonl`
- `data/final/run_summary.yaml`
- `data/final/course_yaml/<course_id>.yaml`

Transient-only run artifacts:
- `data/pipeline_runs/<run_id>/excluded_courses.jsonl`

Publish orchestration rule:
- publish is a required post-flow step of a complete successful pipeline run
- the main processing flow renders transient run artifacts first
- publish then copies the merged successful state into `data/final`

## Logging requirements

The pipeline must emit extensive per-run logs.

Rules:
- every run gets its own log files under the run directory
- logs must be structured and timestamped
- logs must be detailed enough for production-style debugging
- logs must include stage lifecycle events, warnings, errors, row counts, and
  timing data
- logs must capture publish actions into `data/final`
- logs must capture overlap-safe upsert decisions for affected `course_id`s
- logs must capture inspection-bundle creation when that job is run
- for every LLM call, logs must record:
  - stage name
  - configured model
  - requested model
  - actual model returned or confirmed by the API
  - the source used to determine the actual model
  - request id or equivalent provider call id when available
  - latency and token usage when available
- logs must never include secrets or full API keys

Required `logs/llm_calls.jsonl` schema:
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

Required `logs/stage_metrics.jsonl` schema:
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

Recommended run log files:
- `logs/pipeline.log`
- `logs/llm_calls.jsonl`
- `logs/stage_metrics.jsonl`
- `logs/publish.log`
- `logs/inspectgion_bundle.log`

## Inspection bundle job

A dedicated inspection bundle job must exist for curating a small stable subset
from published final outputs.

Contract:
- job name: `mk_inspectgion_bundle`
- accepted argument: digits-only bundle id such as `0`, `1`, `2`, `3`, or
  `011`
- output path: `/tmp/inspectgion_bundl_<bundle_id>`
- source path: `data/final`
- bundle size: exactly 4 courses
- bundle composition:
  - 2 R courses
  - 1 SQL course
  - 1 Python course
- selected courses should emphasize intermediate concepts and remain fixed so
  the bundle is comparable across runs

Required bundle contents:
- filtered copies of all published final artifacts for the selected 4 courses
- filtered per-course YAML files for those same courses
- `pipeline_run_manifest.yaml`
- fail the job if any required selected course output is missing
- allow empty filtered artifact files when they correctly represent the
  published final state for the selected courses

Manifest requirements:
- selected course ids, titles, and language mix
- bundled artifact row counts for each stage
- bundled per-course YAML file counts
- published-run performance data when available
- bundle build timing data
- log ownership metadata for the bundle job

Preferred fixed inspection set:
- `24511` `Categorical Data in the Tidyverse`
- `24662` `Intermediate Functional Programming with purrr`
- `24516` `Improving Query Performance in SQL Server`
- `24458` `Time Series Analysis in Python`

## Suggested evaluation metrics

### Topic extraction
- atomic topic precision
- atomic topic recall
- broad-heading leakage rate
- compound-topic split rate

### Question generation
- sensible question rate
- duplicate intent rate
- reject rate
- entry-question coverage per topic

### Answer stage
- grounded answer rate
- uncertain rate
- false-confidence rate

## Testing requirements

The pipeline must have extensive automated tests.

Priorities:
- unit tests for deterministic stage logic and artifact handling
- regression tests using small fixtures derived from real scraped courses
- edge-case tests for overlap-safe incremental runs
- edge-case tests for final publication and inspection bundle assembly

Minimum required unit-test coverage areas:
- normalization from scraped YAML into `NormalizedCourse`
- atomic topic extraction, especially coordinated heading splits
- canonicalization and duplicate merging rules
- bounded question-pattern expansion and family selection
- repair/reject terminal-state outcomes and reject reasons
- answer correctness labeling and uncertainty handling
- shared-artifact upserts keyed by `course_id`
- `data/final` publish behavior after successful runs
- `mk_inspectgion_bundle` output filtering and manifest counts

## v1 non-requirements

Do not build these first:
- personalization
- speculative serving
- graph database dependency
- adaptive tutoring runtime
- large ontology systems
