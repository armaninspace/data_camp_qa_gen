
# AGENTS.md

## Mission

Build a clean-sheet course-question pipeline from scraped course metadata.

The implementation should generate learner-facing questions and short answers
that are grounded in the course text and easy to inspect.

## Non-negotiable principles

1. Prefer atomic topics over broad headings.
2. Prefer simple bounded pattern expansion over clever free-form generation.
3. Every question candidate must end in an explicit terminal state.
4. Reject unsupported content rather than inventing.
5. Make debugging easy by preserving stage artifacts.
6. Keep file outputs machine-readable and human-inspectable.

## Required pipeline stages

1. normalize course
2. extract atomic topics
3. canonicalize topics
4. expand question patterns
5. repair or reject questions
6. answer accepted questions
7. write ledger rows
8. render per-course YAML bundle
9. render run summary

## Topic extraction guidance

Bad topic units:
- broad chapter headings
- admin labels
- coordinated headings left unsplit when text supports splitting

Good topic units:
- concepts
- procedures
- tools
- metrics or tests
- failure points
- common comparison pairs

Special rule:
If a heading is of the form `X and Y`, split it into separate candidate topics
when the supporting text treats them as distinct ideas.

## Question generation guidance

Use a bounded pattern bank.

Core families:
- entry
- purpose
- mechanism
- procedure
- decision
- comparison
- example
- failure
- interpretation
- prerequisite

Do not force every family onto every topic.
Use topic type to select plausible patterns.

## Validation guidance

Repair allowed:
- grammar cleanup
- article and plurality cleanup
- natural wording adjustment
- minor nudge from awkward template text to learner-facing phrasing

Reject when:
- unsupported by source text
- broad heading only
- compound topic that should have been split upstream
- duplicate intent
- malformed or unnatural
- answer would be too thin to be useful

## Answer guidance

Answers should be:
- short
- direct
- evidence-bound
- conservative

Correctness labels:
- `correct`
- `incorrect`
- `uncertain`

If evidence is weak, prefer `uncertain`.

## Artifact expectations

Persist stage artifacts under one run directory.

Required files:
- `normalized_courses.jsonl`
- `topics.jsonl`
- `question_candidates.jsonl`
- `question_repairs.jsonl`
- `answers.jsonl`
- `all_rows.jsonl`
- `run_summary.yaml`
- `course_yaml/<course_id>.yaml`

## Model recommendations

Use multiple prompts, not one giant prompt.

Recommended:
- `gpt-5.4` for extraction, repair/reject, and answer correctness
- `gpt-5.1-mini` for cheap pattern-conditioned expansion

## Output formats

Prefer JSONL for row artifacts and YAML for per-course bundles.

Wrap prose in docs to about 80 columns where practical.

## Coding style

- Python 3.11+
- use Pydantic v2
- use type hints everywhere
- keep functions small and testable
- isolate LLM calls behind a thin adapter
- avoid hidden magic
- document TODOs explicitly

## First test of success

On a course that mentions `Categorical and Text Data`, the pipeline should be
able to extract `categorical data` and `text data` as separate topics when the
supporting text warrants it, then generate beginner entry questions such as:

- What is categorical data?
- What is text data?

If the pipeline cannot do that, do not add complexity downstream. Fix topic
extraction first.
