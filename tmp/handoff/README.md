# Rewrite Handoff Package

This directory is the self-contained handoff package for the replacement team.

The goal is not to preserve the current implementation. The goal is to give the
next team enough context, examples, failure history, and operator references to
rebuild the pipeline cleanly.

## Start here

Read these in order:

1. `docs/00_project_intent.md`
2. `docs/01_failures_and_lessons.md`
3. `docs/02_target_pipeline_spec.md`
4. `docs/03_testing_and_acceptance.md`
5. `docs/04_ops_and_tooling.md`
6. `docs/05_build_order.md`
7. `docs/06_domain_glossary.md`
8. `docs/07_reference_material_map.md`

## What this package contains

- rewrite intent and target contract
- failure history and lessons from the current repo
- stage-by-stage inputs, outputs, transformations, and invariants
- testing strategy and acceptance criteria
- operator/tooling expectations
- representative raw input course files
- a real small run directory with artifacts and logs
- copied operator scripts
- selected source files and tests from the current repo for reference

## Important boundary

The copied implementation and scripts are reference material only.

They help the next team understand:

- what currently exists
- what failed
- how operators were expected to run the system
- what artifact families need to exist

They do **not** define the replacement architecture. The replacement
architecture is defined by the core docs under `docs/`.
