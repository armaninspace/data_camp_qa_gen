# Codex package: rip out redundant old pipeline parts

This package is a hard-line Codex handoff for removing the old grounded span-answer pipeline and consolidating the repo around one canonical path.

## Package intent

The target end state is:

1. one primary run path
2. LLM-first semantic extraction from the **full normalized course YAML**
3. correlated-topic extraction in the same semantic pass
4. basic single-topic and correlated-topic questions from the same semantic pass
5. short synthetic tutor answers from general knowledge
6. one canonical synthetic-answer path
7. one canonical answer artifact family derived from that path
8. one canonical final ledger / final-row family derived from the same terminal row set
9. no grounded brochure-span answer code anywhere in the main pipeline

Current operational expectations:

- `train_rows.jsonl` and `cache_rows.jsonl` are first-class outputs
- valid semantic synthetic answers propagate into shared `answers.jsonl` and final rows
- filtered inspection bundles are validated against one canonical selection object
- published summaries can report LLM usage and cost when run logs were published

## Package contents

- `AGENTS.md` — repo-root Codex instructions
- `CODEX_TASK.md` — explicit engineering task brief
- `DELETE_LIST.md` — what to remove now
- `TARGET_ARCHITECTURE.md` — what remains after removal
- `LLM_SEMANTIC_STAGE_SPEC.md` — full-course YAML prompt-stage requirements
- `ACCEPTANCE_CRITERIA.md` — hard done conditions
- `TEST_PLAN.md` — regression and migration tests

## Non-goals

- preserving the old grounded answer path as fallback
- dual-write migration beyond what is strictly needed to land the deletion safely
- keeping backward-compat artifact aliases that have no real consumer
- polishing answer prompts before semantic extraction and final-output consistency are fixed

## Core rule

The old grounded-answer path is **disallowed**, not merely deprecated.
