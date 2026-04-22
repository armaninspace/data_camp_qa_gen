# Domain Glossary

## Raw course

The scraped YAML/JSON source file before any normalization.

## Preflight

The quality classification step that decides whether a raw course is runnable.

## Normalized course

The stable typed representation used by all later stages.

## Semantic stage

The full-course LLM pass that returns:

- topics
- correlated topics
- single-topic questions
- correlated-topic questions
- short synthetic answers

## Semantic review

The optional cleanup pass that can rewrite, merge, or reject semantic items.

## Policy stage

The narrow post-semantic stage that canonicalizes families, preserves
provenance, and reports informational coverage/anchor state.

## Course context frame

Course-level machine-usable context used to condition answer generation.

## Question context frame

Question-level machine-usable context including support refs and expected answer
shape.

## Teacher answer draft

The generated answer draft produced from provided context for a question.

## Answer record

The one canonical answer object that should back surfaced answered rows.

## Train row

A retained context-carrying row intended for training-data downstream use.

## Cache row

A retained context-carrying row intended for serving/retrieval-style downstream
use.

## Ledger row / final row

The terminal surfaced row for a question, with one final status:

- answered
- rejected
- errored

## Shared artifacts

The JSONL files written at the run or published level that aggregate rows
across courses.

## Per-course YAML

The course-local inspection/debug bundle for one course.

## Publish

The process of merging successful run outputs into stable `data/final`.

## Inspection bundle

A filtered or full projection of published outputs for QA/debugging.
It is not the primary truth source.
