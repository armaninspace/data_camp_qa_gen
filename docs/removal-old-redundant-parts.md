# Plan To Remove Old Redundant Pipeline Parts

## Goal

Cut the parts of the current pipeline that only exist to preserve the older
grounded-answer publish path, while keeping enough structure to ship a simpler
pipeline built around:

1. normalized course scope
2. atomic topic extraction
3. question validation
4. frontier answer synthesis
5. inspectable final artifacts

This is a removal plan, not an implementation diff.

## Why This Is Needed

The repo currently has two answer paths:

- the default `run` flow still uses `answer_questions()` and publishes
  `grounded_course_answer` rows into `data/final`
- the newer frontier work lives beside it in `synthesize_answers.py` and is
  only reachable through separate CLI commands

That split creates redundant code, redundant artifacts, and product confusion.
The repo now needs one primary path.

## Target End State

The main pipeline should:

1. run one course-processing flow
2. generate validated learner questions
3. synthesize short tutor answers with the frontier path
4. validate/rewrite/reject those answers
5. publish per-course YAML and shared artifacts from that path

The older evidence-span answer path should stop being the source of published
course answers.

## Keep vs Remove

## Keep

- preflight validation
- normalization
- atomic topic extraction
- canonicalization
- related-pair discovery only if still used by the retained question families
- topic vetting if it still removes bad headings and broad wrappers
- question generation and validation
- run logging
- upsert-based publish behavior
- per-course YAML output
- inspection bundle job, but updated to read the new final artifact set

## Remove Or Collapse

- `answer_questions()` as the publish-time answer source
- grounded-only answer artifacts as the canonical final answer record
- legacy candidate/repair shims that exist only to backfill old artifact names
- duplicate CLI paths that force operators to run a second synthetic stage by
  hand after the main run
- summary metrics that only make sense for evidence-span answers
- artifact duplication where the same row is represented in both old and new
  formats without a real consumer

## Specific Candidates For Removal

## 1. Old grounded answer stage

Primary candidate:

- `src/course_pipeline/tasks/answer_questions.py`

Why remove:

- it answers by copying a support span from course text
- it is the reason published bundles still contain old brochure-snippet answers
- it duplicates the responsibility of the newer synthesis path

Replacement:

- synthetic answer generation plus validation becomes the only answer stage used
  by the main flow

## 2. Main-flow wiring to grounded answers

Primary candidate:

- `course_question_pipeline_flow()` calling `answer_questions()`

Why remove:

- it keeps the old path as the default publish path
- it forces the new frontier path to remain a sidecar workflow

Replacement:

- wire synthetic answer generation directly into the main flow before ledger
  rendering and publish

## 3. Legacy compatibility adapters

Primary candidates:

- `_legacy_candidates()`
- `_legacy_repairs()`

Why remove:

- these exist to translate newer question-validation objects back into older
  artifact shapes
- they add indirection with little value if the final artifact contract is
  updated

Replacement:

- use one canonical question-validation schema end to end

## 4. Old answer artifact contract

Primary candidates:

- `answers.jsonl` in its current grounded-answer shape
- `AnswerRecord` defaulting to `grounded_course_answer`
- `final_rows` / ledger rows assuming the old answer source

Why remove or reshape:

- the old schema bakes in the grounded-answer mode as the default
- published YAML bundles mirror that old answer mode

Replacement:

- redefine the final answer record around validated synthetic answers
- keep explicit answer mode, but make the synthetic mode the standard path

## 5. Separate synthetic CLI choreography

Primary candidates:

- `run-synthetic-answering`
- `build-ft-dataset`
- `render-ft-bundle`

Why remove or demote:

- these commands are useful for debugging, but they should not be required to
  obtain the primary final output
- operators should not need a second pipeline after `run`

Replacement:

- keep debug entrypoints if useful, but make them wrappers around shared stage
  functions used by the main flow

## 6. Redundant published artifacts

Primary candidates for review:

- `question_candidates.jsonl`
- `question_repairs.jsonl`
- `answers.jsonl`
- any old-only artifacts no longer needed once validated questions and
  validated synthetic answers exist

Why review:

- some of these are historical stage names rather than necessary user-facing
  products
- the repo should keep inspectable stage artifacts, but not two names for the
  same stage outcome

Likely direction:

- keep one validated-question artifact
- keep one final-answer artifact
- keep one final ledger artifact
- drop aliases that only exist for backward compatibility

## Proposed Removal Sequence

## Phase 1. Freeze The New Canonical Path

Decisions to make first:

- Is the frontier synthetic answer path now the default publish path?
- Should `data/final/course_yaml/*.yaml` contain only synthetic answers, or
  both synthetic answers and question-validation detail?
- Which shared artifacts are true contract files versus transitional files?

Deliverables:

- a short artifact contract doc
- one declared final answer schema
- one declared final per-course YAML schema

Do not remove code before this decision is written down.

## Phase 2. Integrate Synthetic Answering Into The Main Flow

Changes:

- add synthetic answer generation and validation directly into
  `course_question_pipeline_flow()`
- make ledger construction consume validated synthetic answers
- render published course YAML from synthetic answer results

Acceptance:

- after a normal `run`, published course bundles show
  `answer_mode: synthetic_tutor_answer`
- no separate post-run synthetic command is required for standard outputs

## Phase 3. Remove Grounded Answer Publish Logic

Changes:

- stop calling `answer_questions()` from the main flow
- stop using grounded answer rows as the source for `answers.jsonl`
- remove grounded-answer-specific summary logic if it has no remaining consumer

Acceptance:

- the main flow still produces terminal row states
- `data/final` no longer depends on evidence-span answer copying

## Phase 4. Collapse Legacy Question Artifacts

Changes:

- remove `_legacy_candidates()` and `_legacy_repairs()`
- rename or consolidate question-stage artifacts so the pipeline uses one
  canonical validated-question representation

Acceptance:

- question artifacts are easier to inspect
- no duplicate rows exist solely because of backward compatibility naming

## Phase 5. Prune Dead CLI And Docs Surface

Changes:

- demote stage-specific synthetic commands to debug-only tools, or remove them
  if they duplicate internal flow behavior
- update `README.md`, `docs/architecture.md`, and operation docs to describe one
  primary run path

Acceptance:

- a new operator can tell from the docs which command produces the real final
  outputs

## Phase 6. Remove Dead Tests And Add Migration Tests

Remove or rewrite tests that lock in the old behavior:

- tests asserting grounded answer defaults
- tests assuming final bundles publish brochure-span answers
- tests expecting old compatibility artifacts if those artifacts are removed

Add:

- tests proving `run` publishes synthetic tutor answers
- tests proving per-course YAML and shared artifacts remain in sync
- tests proving inspection bundles still work after artifact consolidation

## Risks

## Risk 1. Removing useful evidence entirely

The old grounded path is redundant as the answer source, but its evidence spans
are still useful as scope and audit metadata.

Mitigation:

- preserve course-derived evidence and question provenance in the bundle
- remove grounded answering, not source-text provenance

## Risk 2. Breaking incremental publish behavior

The upsert and merged-summary behavior is operationally important and should not
be touched unless required.

Mitigation:

- keep `course_id`-based upsert logic unchanged during answer-path removal

## Risk 3. Cutting pairwise logic too early

Some pairwise and vetting stages may still be needed by the retained question
families.

Mitigation:

- remove only after confirming actual usage in generated questions and tests

## Risk 4. Leaving the repo half-migrated

The current state is already split between old publish behavior and new
synthetic sidecar behavior.

Mitigation:

- do not start by deleting code
- first make the synthetic path the default path
- only then remove the grounded path and compatibility shims

## Recommended First PR

The first removal-oriented PR should do only this:

1. integrate synthetic answering into the main `run` flow
2. render synthetic answers into `course_yaml`
3. keep old artifacts temporarily if needed for compatibility
4. add tests that prove published bundles now use synthetic answers

That PR creates a safe base for later deletions.

## Recommended Second PR

The second PR should:

1. delete `answer_questions.py` from the main flow
2. remove grounded-answer defaults from schemas
3. remove old compatibility adapters
4. simplify artifact rendering

## Definition Of Completion

This cleanup is complete when:

- one primary run command produces the real final outputs
- published course bundles no longer use the old grounded answer path
- there is one canonical answer artifact family
- there is one canonical validated-question artifact family
- operators no longer need to understand two competing pipelines
- tests no longer preserve obsolete grounded-answer behavior as the default
