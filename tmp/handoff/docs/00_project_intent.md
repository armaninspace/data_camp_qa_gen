# Project Intent

## What this project is for

The project takes scraped course metadata and turns it into reusable,
learner-facing question/answer assets.

The intended products are:

- surfaced answered rows for inspection and downstream use
- `train_rows.jsonl` for training data creation
- `cache_rows.jsonl` for serving/retrieval-oriented use
- per-course YAML bundles for debugging and inspection
- merged published outputs in `data/final`
- optional inspection bundles for QA

## The intended user experience

For each course, the system should be able to produce:

- a set of learner-facing concepts and related concept pairs
- useful beginner and comparison questions
- short, direct answers appropriate to the course level
- context-carrying rows that preserve course framing

## What the final system should optimize for

1. One canonical pipeline path.
2. One canonical answer representation.
3. Inspectable provenance on surfaced answers.
4. Deterministic slice runs and predictable publish behavior.
5. Trustworthy summaries and bundle validation.

## What the final system should not optimize for

- preserving old grounded brochure-span answer behavior
- maximizing backward compatibility with stale artifacts
- hiding multiple runtime paths behind shims
- relying on filtered inspection bundles as the main truth source

## Canonical high-level runtime

```text
raw course file
-> preflight
-> normalized course
-> full-course semantic extraction
-> policy / canonicalization / dedupe
-> context frames
-> answer generation
-> terminal row assembly
-> render per-run artifacts
-> publish merged final outputs
-> optional inspection bundle projection
```

## Primary final outputs

- `train_rows.jsonl`
- `cache_rows.jsonl`
- `answers.jsonl`
- `all_rows.jsonl`
- `course_yaml/<course_id>.yaml`
- `run_summary.yaml`

## Why a rewrite is justified

The current repo demonstrated that the product direction is reasonable, but the
implementation accumulated drift between:

- the runtime and the docs
- semantic artifacts and surfaced artifacts
- full-run truth and filtered projections
- metrics and real schema

The rewrite should simplify around a clean single contract instead of trying to
patch that drift indefinitely.
