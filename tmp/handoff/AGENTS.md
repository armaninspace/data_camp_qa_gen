# AGENTS.md

## Mission

Simplify this repo into one primary pipeline and rip out redundant old pipeline parts.

The old grounded brochure-span answer path is **not allowed** in the final state.

## Mandatory rules

1. Do **not** preserve `answer_questions()` as a hidden fallback.
2. Do **not** publish or render brochure-span answers anywhere in final outputs.
3. Do **not** keep backward-compat artifact aliases unless there is an active consumer.
4. Do **not** add more shims to preserve obsolete behavior.
5. Do **not** treat the old and new answer paths as co-equal. There must be one canonical answer path.

## Required target architecture

The primary run should be:

`normalize -> full-course LLM semantic stage -> canonicalize/vet/dedupe -> validated questions -> synthetic tutor answers -> final rows -> shared artifacts + per-course YAML + inspection bundle`

## Full-course LLM semantic stage

The semantic stage should send the **entire normalized course YAML** to the LLM in one structured prompt.

In that same prompt, the model should return:

- primary learner-facing topics
- heavily correlated topics
- basic single-topic questions
- basic correlated-topic questions
- short synthetic tutor answers from general knowledge

This is the primary semantic source. Do not rely on shallow lexical topic extraction as the default path.

## Hard removal mandate

Remove or disconnect:
- `src/course_pipeline/tasks/answer_questions.py`
- main-flow wiring that calls the grounded answer path
- grounded-answer-first schema defaults
- obsolete legacy candidate/repair compatibility shims
- summary/report logic that only makes sense for grounded span answers
- duplicate artifacts that preserve the old pipeline without a real consumer

## Output consistency rule

Shared artifacts and per-course YAML must be derived from the **same terminal row set**.
Fail fast on mismatch.

## Semantic quality rule

Reject topics/questions like:
- `where`
- `getting started in python`
- `different types of plots`
- `learn to manipulate dataframes`

Recover learner-facing concepts like:
- `pandas`
- `matplotlib`
- `dictionary`
- `control flow`
- `loop`
- `filtering`

## What to report back

Every Codex response should include:
- root cause found
- files changed
- what was deleted
- what final artifacts changed
- tests added/updated
- any remaining risks
