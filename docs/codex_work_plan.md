
# Codex Work Plan

## Phase 1

Make the baseline run end to end with deterministic logic and correct
incremental artifact behavior.

Deliver:
- package and CLI wiring works from repo root
- flow runs on sample data
- flow runs on real scraped DataCamp YAML input
- broken scraped courses are excluded before main processing
- slice selection is deterministic and reproducible
- artifacts are written
- overlapping slice runs overwrite only intersecting course data
- non-overlapping artifact rows are preserved across reruns
- per-course YAML renders
- run summary is rebuilt from merged artifact state
- final workproducts are published to `data/final` after successful runs
- publish is implemented as a required post-flow step
- transient run artifacts stay outside the checked-in publish path
- inspection bundle job writes `/tmp/inspectgion_bundl_<id>` from `data/final`
- inspection manifest reports performance data and stage counts
- extensive per-run logs are written under each run directory
- LLM call logs capture the actual model used at runtime
- extensive unit tests pass

## Phase 2

Replace deterministic topic extraction with OpenAI structured output.

Deliver:
- typed topic extraction call
- better split of compound headings
- broader evidence capture
- regression tests on real scraped courses
- regression tests on a small labeled set

## Phase 3

Replace deterministic repair and answer stages with OpenAI calls.

Deliver:
- question repair/reject prompt
- conservative answer prompt
- correctness labeling
- uncertainty handling
- explicit evidence payloads on answers

## Phase 4

Add evaluation and diagnostics.

Deliver:
- stage-level metrics
- summary dashboard or markdown report
- sampled error examples
- slice-run overwrite integrity checks

## Detailed slices

1. Repo wiring
- make `course_pipeline` importable in tests and local runs
- add stable run commands for sample and real corpus slices
- make pytest run cleanly from the repo root
- define and document deterministic slice selection
- normalize input paths before slice ordering

2. Preflight validation
- classify scraped courses as `usable`, `partial`, or `broken`
- exclude `broken` records from the runnable course set
- write `excluded_courses.jsonl`
- add unit tests for malformed-title and no-content exclusion

3. Real input normalization
- normalize `datacamp_data/classcentral-datacamp-yaml`
- preserve evidence-bearing fields and malformed data safely
- add unit tests with real scraped fixtures

4. Incremental artifact store
- add `course_id`-based upsert for all shared JSONL artifacts
- add `canonical_topics.jsonl`
- rebuild summaries from merged state
- add overlap and non-overlap unit tests

5. Logging foundation
- add per-run `logs/` outputs with pipeline and stage logs
- add structured LLM call logging
- capture configured model, requested model, and actual model used
- define `actual_model` precedence and provenance logging
- lock the JSONL log schemas in code and tests
- add tests for log-file creation and log-record shape

6. Final publish step
- copy merged outputs from successful runs into `data/final`
- apply the same overlap-safe upsert semantics in `data/final`
- keep transient run artifacts separate from published checked-in outputs
- enforce publish-success criteria and log blocked publish attempts
- add publish-merge unit tests

7. Inspection bundle job
- add `mk_inspectgion_bundle <digits>` CLI or job entrypoint
- build `/tmp/inspectgion_bundl_<id>` from `data/final`
- include exactly 4 stable intermediate courses: 2 R, 1 SQL, 1 Python
- write `pipeline_run_manifest.yaml` with performance data and artifact counts
- define bundle-scoped logging ownership
- fail if any required selected course output is missing
- allow empty filtered artifacts when they accurately reflect selected-course
  outputs
- add unit tests for bundle filtering and manifest counts

8. Deterministic extraction baseline
- improve heading parsing and coordinated split behavior
- reject broad headings earlier
- add unit tests for atomic-topic extraction behavior

9. Structured topic extraction
- implement OpenAI-backed extraction behind the thin adapter
- add labeled regression cases for compound split behavior

10. Canonicalization hardening
- separate display labels and normalized labels
- merge obvious duplicates conservatively

11. Question expansion hardening
- ensure entry-question coverage for strong topics
- limit families and comparisons to plausible cases
- add unit tests for family selection and duplicate intent prevention

12. Repair/reject LLM stage
- implement structured repair-or-reject with explicit reject reasons
- add tests for terminal-state mapping and reject-reason handling

13. Answer LLM stage
- implement conservative evidence-bound answers with correctness labels
- add tests for correctness labeling and uncertain fallback

14. Evaluation and corpus runs
- run on representative slices of the scraped corpus
- measure extraction, question, answer, incremental-overwrite, and final-publish
  quality
- verify inspection bundle stability and manifest completeness
