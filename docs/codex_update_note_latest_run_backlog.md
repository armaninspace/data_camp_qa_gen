# Backlog From `codex_update_note_latest_run.md`

This backlog translates the latest-run review into concrete follow-up work.

## Assessment

The update note is directionally correct.

Its strongest point is the causal chain:

```text
bad topic -> accepted topic -> accepted question -> polished synthetic answer
```

That is the right failure model to optimize against.

The note is also useful because it correctly deprioritizes answer-prompt tuning.

## What Is Already Partly Addressed

These items are no longer the main blockers, but still need verification in a
fresh run:

- synthetic answers are now the main runtime answer path
- shared synthetic artifacts are published
- bundle filtering includes synthetic shared artifacts
- validator score normalization now handles `1..5` to `0..1`
- obvious junk prefixes such as `getting started in`, `learn to`, and
  `different types of` are now filtered more aggressively

These should be treated as "verify in real outputs", not "start from zero".

## What Still Looks Worth Working On

Yes, this is worth working on.

The highest-value remaining work is:

1. tighten topic extraction and vetting further
2. add a stricter pre-answer legitimacy gate for validated questions
3. verify fresh-run artifact consistency after the cutover
4. harden validator score semantics beyond simple numeric normalization

## Slice 1: Fresh-Run Verification

Status: pending

Goal:

- confirm the current code actually produces clean shared outputs on a fresh run

Tasks:

- run a fresh 1% slice from an empty `data/`
- inspect:
  - `answers.jsonl`
  - `synthetic_answers.jsonl`
  - `synthetic_answer_validation.jsonl`
  - `run_summary.yaml`
  - `course_yaml/*.yaml`
- verify shared artifacts, per-course YAML, and run summary agree

Acceptance:

- no mismatch between per-course YAML and shared answer artifacts
- no grounded-answer rows in final outputs

## Slice 2: Topic-Rejection Hardening

Status: pending

Goal:

- stop obviously illegitimate topics before question generation

Tasks:

- expand extraction-time blocklists for wrapper and imperative headings
- add vetting-time rejection for:
  - discourse fragments
  - generic wrapper phrases
  - verb-headed labels unless explicitly whitelisted
  - generic category phrases that are not actual learner topics
- add regression fixtures from the latest bad outputs

Examples to protect against:

- `where`
- `getting started in python`
- `different types of plots`
- `learn to manipulate dataframes`

Acceptance:

- these labels do not survive to accepted vetted topics

## Slice 3: Question Legitimacy Gate

Status: pending

Goal:

- reject malformed or illegitimate learner questions before answer synthesis

Tasks:

- add a stricter validation gate after question generation and before synthesis
- reject questions when:
  - the topic label is wrapper-like
  - the topic label is discourse-like
  - the topic label is imperative or marketing phrasing
  - the final question is grammatical only because the model could reinterpret
    it using outside knowledge
- add direct tests for bad outputs like:
  - `What is where?`
  - `What is different types of plots?`

Acceptance:

- malformed entry questions do not reach synthetic answer generation

## Slice 4: Vetted-Question Artifact Tightening

Status: pending

Goal:

- make accepted question artifacts explicitly encode legitimacy decisions

Tasks:

- consider adding explicit fields to `question_validation.jsonl` such as:
  - `legitimacy_status`
  - `legitimacy_reason`
- separate grammar repair from legitimacy acceptance
- keep terminal state explicit for each generated question

Acceptance:

- it is easy to see why a question was accepted or blocked before synthesis

## Slice 5: Validator Semantics Cleanup

Status: pending

Goal:

- make validator scoring interpretable and stable

Tasks:

- document all validator score fields and their meaning
- define one canonical numeric range for every field
- distinguish:
  - quality scores
  - risk scores
  - acceptance thresholds
- reject or normalize any malformed validator payloads

Acceptance:

- no mixed-scale validator rows in final artifacts
- accept / rewrite / reject decisions are explainable from documented thresholds

## Slice 6: Real-Run Quality Review

Status: pending

Goal:

- validate that the upstream legitimacy fixes improve real outputs

Tasks:

- rerun 1%
- inspect a small hand-reviewed sample of:
  - topics
  - vetted topics
  - question validation rows
  - final course YAML bundles
- count how many garbage topics and malformed questions still survive

Acceptance:

- clear reduction in accepted junk topics and junk questions

## Recommended Order

1. Fresh-run verification
2. Topic-rejection hardening
3. Question legitimacy gate
4. Validator semantics cleanup
5. Real-run quality review

## Non-Goals

Still not the right focus for the next pass:

- richer pairwise reasoning
- broader question family expansion
- answer-style tuning
- answer verbosity tuning

Those come after legitimacy is under control.
