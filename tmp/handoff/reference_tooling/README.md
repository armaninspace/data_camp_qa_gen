# Reference Tooling

This directory collects current operator scripts, selected source files, and
selected tests from the existing repo.

The goal is to expose:

- current CLI surfaces
- current run/publish/bundle workflows
- current schema and task boundaries
- regression tests that capture failure history

This is reference material for the rewrite team. It is not a mandate to carry
forward the current implementation structure unchanged.

## Contents

- `scripts/`: operator-facing shell entrypoints
- `src/course_pipeline/`: selected implementation files and prompts
- `tests/`: selected regression tests that describe important behavior
- copied repo root policy/config files where useful
