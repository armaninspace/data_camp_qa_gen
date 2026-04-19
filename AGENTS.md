
# AGENTS.md

## Mission

Build a clean-sheet course-question pipeline from scraped course metadata.

The implementation should generate learner-facing questions and short answers
that are grounded in the course text and easy to inspect.

## Non-negotiable principles

1. Prefer atomic topics over broad headings.
2. Prefer simple bounded pattern expansion over clever free-form generation.
3. Every question candidate must end in an explicit terminal state.
4. Reject unsupported content rather than inventing.
5. Make debugging easy by preserving stage artifacts.
6. Keep file outputs machine-readable and human-inspectable.

## Required pipeline stages

1. normalize course
2. extract atomic topics
3. canonicalize topics
4. expand question patterns
5. repair or reject questions
6. answer accepted questions
7. write ledger rows
8. render per-course YAML bundle
9. render run summary

The inspection bundle is not one of the core 9 stages.
It is a separate post-publish job that reads from `data/final`.

## Topic extraction guidance

Bad topic units:
- broad chapter headings
- admin labels
- coordinated headings left unsplit when text supports splitting

Good topic units:
- concepts
- procedures
- tools
- metrics or tests
- failure points
- common comparison pairs

Special rule:
If a heading is of the form `X and Y`, split it into separate candidate topics
when the supporting text treats them as distinct ideas.

## Question generation guidance

Use a bounded pattern bank.

Core families:
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

Do not force every family onto every topic.
Use topic type to select plausible patterns.

## Validation guidance

Repair allowed:
- grammar cleanup
- article and plurality cleanup
- natural wording adjustment
- minor nudge from awkward template text to learner-facing phrasing

Reject when:
- unsupported by source text
- broad heading only
- compound topic that should have been split upstream
- duplicate intent
- malformed or unnatural
- answer would be too thin to be useful

## Answer guidance

Answers should be:
- short
- direct
- evidence-bound
- conservative

Correctness labels:
- `correct`
- `incorrect`
- `uncertain`

If evidence is weak, prefer `uncertain`.

## Artifact expectations

Persist stage artifacts under one run directory.

Incremental runs must be supported.

If a new run processes only a slice of courses, it must overwrite only the
overlapping course data in shared artifacts and preserve non-overlapping course
data already present in the output directory.

Special rule for overlap:
- treat `course_id` as the primary upsert key for course-scoped artifacts
- when rerunning a slice, remove prior rows for the affected `course_id`s and
  replace them with the newly generated rows
- do not duplicate rows for overlapping courses
- do not rewrite unrelated course outputs
- rebuild run summaries from the merged post-upsert artifact state, not only
  from the latest slice

Slice-selection rules:
- slice boundaries must resolve against a stable deterministic ordering of the
  corpus
- the default corpus ordering is lexicographic by input file path
- input paths must be normalized relative to the chosen input root before
  ordering
- a slice definition must be reproducible across runs given the same input
  corpus snapshot and ordering rule
- overlap is defined by intersecting `course_id`s after slice expansion, not
  by percent labels alone

Completed runs must also publish final workproducts to `data/final`.

Publication rules:
- `data/final` is the checked-in output location intended for git
- transient run artifacts under `data/pipeline_runs/<run_id>/` are not intended
  for git
- only copy outputs to `data/final` after a full successful pipeline run
- published outputs in `data/final` must reflect the merged post-upsert state
- publishing a new successful run must overwrite only the overlapping
  course-scoped outputs in `data/final` and preserve non-overlapping outputs

Success rules for publish:
- publish is allowed only when every course in the current run reaches a final
  course-level outcome
- acceptable course-level outcomes for publish are:
  - fully processed with terminal row states only
  - processed with some question rows marked `rejected`
  - processed with some question rows marked `errored`, if the course still
    completed and artifacts were rendered
- publish must be blocked when:
  - the run crashes before artifact rendering finishes
  - any selected input course has no rendered course bundle
  - shared artifacts and per-course bundles are out of sync for the current run
- blocked publish attempts must be logged explicitly

Required files:
- `normalized_courses.jsonl`
- `topics.jsonl`
- `canonical_topics.jsonl`
- `question_candidates.jsonl`
- `question_repairs.jsonl`
- `answers.jsonl`
- `all_rows.jsonl`
- `run_summary.yaml`
- `course_yaml/<course_id>.yaml`

Every pipeline run must also produce dedicated run logs.

Logging requirements:
- logs must be written under the run directory for each pipeline run
- each run must have separate log files; do not mix logs across runs
- logs should be structured, timestamped, and suitable for operational
  debugging
- include stage start, stage completion, warnings, errors, row counts, and
  timing data
- log publish-to-`data/final` actions and overlap/upsert decisions
- log inspection-bundle creation steps and manifest counts
- log every LLM call with the actual model identifier used at runtime
- distinguish configured model, requested model, and actual returned model when
  they differ
- include request ids or call ids when available from the provider
- never log secrets or full API keys

Structured log schemas must be stable.

Required `logs/llm_calls.jsonl` fields:
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

Required `logs/stage_metrics.jsonl` fields:
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

Preferred run log files:
- `logs/pipeline.log`
- `logs/llm_calls.jsonl`
- `logs/stage_metrics.jsonl`
- `logs/publish.log`
- `logs/inspectgion_bundle.log`

Published final files under `data/final`:
- `normalized_courses.jsonl`
- `topics.jsonl`
- `canonical_topics.jsonl`
- `question_candidates.jsonl`
- `question_repairs.jsonl`
- `answers.jsonl`
- `all_rows.jsonl`
- `run_summary.yaml`
- `course_yaml/<course_id>.yaml`

An inspection bundle job must exist:
- job name: `mk_inspectgion_bundle`
- argument: digits-only bundle id such as `0`, `1`, `2`, `3`, or `011`
- output directory: `/tmp/inspectgion_bundl_<bundle_id>`
- input source: `data/final`
- the bundle must contain final outputs for exactly 4 courses:
  - 2 R courses
  - 1 SQL course
  - 1 Python course
- selected courses should emphasize intermediate concepts and remain stable
  across runs so bundle diffs are meaningful
- the bundle must include a `pipeline_run_manifest.yaml` with:
  - selected course metadata
  - performance data from the published run when available
  - row counts for each bundled artifact stage
  - file counts for bundled per-course YAML outputs
- the job must fail if any of the 4 required selected course outputs are
  missing from `data/final`
- empty filtered artifact files are allowed when they accurately reflect the
  selected courses' published final state

Preferred fixed inspection set:
- `24511` `Categorical Data in the Tidyverse` (R)
- `24662` `Intermediate Functional Programming with purrr` (R)
- `24516` `Improving Query Performance in SQL Server` (SQL)
- `24458` `Time Series Analysis in Python` (Python)

## Model recommendations

Use multiple prompts, not one giant prompt.

Recommended:
- `gpt-5.4` for extraction, repair/reject, and answer correctness
- `gpt-5.4-mini` for cheap pattern-conditioned expansion

## Output formats

Prefer JSONL for row artifacts and YAML for per-course bundles.

Wrap prose in docs to about 80 columns where practical.

## Coding style

- Python 3.11+
- use Pydantic v2
- use type hints everywhere
- keep functions small and testable
- isolate LLM calls behind a thin adapter
- avoid hidden magic
- document TODOs explicitly

## Testing requirements

Extensive unit tests are required.

At minimum, the codebase must include strong unit coverage for:
- normalization of real scraped course records
- coordinated-topic splitting and topic canonicalization
- bounded question expansion rules
- repair-or-reject terminal-state behavior
- answer labeling for `correct`, `incorrect`, and `uncertain`
- `course_id`-based upsert behavior for overlapping slice runs
- publish-to-`data/final` behavior
- `mk_inspectgion_bundle` bundle assembly and manifest counts

Testing guidance:
- prefer fast deterministic unit tests for stage logic
- add focused fixtures from real scraped DataCamp records
- use regression tests for key intermediate-course examples
- test both happy paths and overlap/partial-data edge cases

## First test of success

On a course that mentions `Categorical and Text Data`, the pipeline should be
able to extract `categorical data` and `text data` as separate topics when the
supporting text warrants it, then generate beginner entry questions such as:

- What is categorical data?
- What is text data?

If the pipeline cannot do that, do not add complexity downstream. Fix topic
extraction first.
