
# Course Question Pipeline Starter

A clean-sheet starter project for building a course-question pipeline from
scraped course metadata.

This repo is designed to be handed to Codex or a developer as a kickoff
bundle. It favors simple, inspectable stages over inherited complexity.

## Goal

Input: scraped course YAML or JSON.

Output: structured learner-facing question and answer artifacts grounded in the
course text.

Final row shape:

`<course, [relevant_topics], question_text, question_answer, correctness>`

## Core idea

1. Normalize the scraped course record.
2. Extract atomic topics and entities.
3. Generate question candidates from a bounded pattern bank.
4. Repair or reject weak questions.
5. Answer accepted questions conservatively.
6. Write one authoritative ledger plus per-course inspection YAML.

## Why this exists

The previous direction over-invested in complicated downstream logic before
proving the simple baseline:

- can we extract the right atomic topics?
- can we generate obvious beginner questions from them?
- can we make every question end in an explicit terminal state?

This starter repo resets to that baseline.

## Suggested stack

- Python 3.11+
- Prefect for orchestration
- Pydantic v2 for schemas
- OpenAI SDK for model calls
- Typer for CLI
- JSONL for run artifacts
- YAML for per-course inspection outputs

## Recommended models

Use multiple prompts rather than one giant prompt.

- `gpt-5.4`
  - atomic topic extraction
  - repair or reject
  - answer generation and correctness judgment

- `gpt-5.4-mini`
  - pattern-conditioned question generation
  - cheap high-volume expansion
  - optional paraphrase work

A single-prompt baseline can be kept for comparison, but it should not be the
canonical path.

## Project layout

```text
src/course_pipeline/
  flows/
  tasks/
  prompts/
  schemas.py
  pattern_bank.py
  cli.py

data/
  scraped/
  pipeline_runs/

docs/
  clean_sheet_spec.md
  architecture.md

tests/
```

## Quick start

1. Create a virtual environment.
2. Install dependencies.
3. Copy `.env.example` to `.env`.
4. Put scraped course files in `data/scraped/`.
5. Run the pipeline.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
python -m course_pipeline.cli run   --input data/scraped   --output data/pipeline_runs/dev_run
```

## What is implemented in this starter

- repo structure
- schemas
- prompt files
- pattern bank
- Prefect flow skeleton
- task skeletons
- CLI entrypoint
- artifact writers
- sample course file
- tests for simple rules

## What is not implemented yet

- real OpenAI structured output calls
- production retry and rate-limit handling
- topic dedupe via embeddings
- rich policy engine
- personalization
- speculative serving
- adaptive tutoring runtime

## Acceptance criteria for v1

The first useful version is acceptable when:

1. it extracts atomic topics better than a broad-heading baseline
2. every retained topic gets at least one sensible entry question
3. coordinated headings like `X and Y` split when warranted
4. every candidate reaches a terminal state
5. outputs are easy to inspect in JSONL and YAML
6. the ledger can be rebuilt from stage artifacts

## Hand this to Codex

This repo is meant to be a clean-sheet build target.

Do not port old question-generation logic line by line.
Use the scraped data as substrate and re-derive the implementation from the
requirements in `docs/clean_sheet_spec.md` and `AGENTS.md`.
