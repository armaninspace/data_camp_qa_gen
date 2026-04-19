
# Clean-Sheet Pipeline Spec

## Goal

Build a pipeline that turns scraped course metadata into grounded,
learner-facing question and answer artifacts.

Final row shape:

`<course, [relevant_topics], question_text, question_answer, correctness>`

## High-level flow

```text
raw course yaml/json
-> normalized course
-> atomic topics/entities X
-> question candidates Q from patterns P
-> repaired or rejected questions Q2
-> answers + correctness labels
-> authoritative ledger
-> inspection bundle
```

## Why multiple prompts

Use multiple prompts.

Recommended split:
- Prompt A: atomic topic extraction
- Prompt B: question generation from topics and patterns
- Prompt C: repair or reject
- Prompt D: answer and judge correctness

Reasons:
- easier debugging
- cleaner retries
- clearer metrics
- lower blast radius for failure

## Stage 1: Normalize course

Input:
- raw scraped YAML or JSON

Output:
- `NormalizedCourse`

Rules:
- preserve source text for evidence
- infer chapters from overview if syllabus is missing
- keep confidence on inferred chapter recovery
- never silently drop malformed fields

## Stage 2: Extract atomic topics

Goal:
- return learner-facing atomic topics, not just chapter headings

Prefer:
- concepts
- procedures
- tools
- metrics/tests
- failure points
- explicit comparison pairs

Reject or down-rank:
- vague headings
- admin labels
- broad coordinated phrases left unsplit

Special rule:
If a heading is `X and Y`, split when the supporting text treats them as
distinct ideas.

## Stage 3: Canonicalize topics

Goal:
- merge obvious duplicates
- normalize labels
- keep display label and normalized label separate

Embeddings are optional in v1.

## Stage 4: Pattern bank

Use a bounded question pattern bank.

Families:
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

## Stage 5: Generate question candidates

Input:
- canonical topics
- topic types
- pattern bank
- topic relations when available

Rules:
- every strong topic gets at least one entry question
- not every family applies to every topic
- do not generate awkward questions from broad labels

## Stage 6: Repair or reject

For each candidate:
- accept
- repair slightly
- reject with explicit reason

Allowed repairs:
- grammar
- articles
- plurality
- natural wording nudge

Not allowed:
- introducing unsupported concepts
- changing the intent beyond a small nudge

Reject reasons:
- unsupported
- broad_heading
- compound_topic
- duplicate_intent
- malformed
- unnatural
- thin_answer

## Stage 7: Answer and rate correctness

For each accepted question:
- answer conservatively from course evidence
- rate `correct`, `incorrect`, or `uncertain`

If evidence is weak, prefer `uncertain`.

## Stage 8: Build ledger

Every generated question candidate must end in a terminal state.

Terminal states:
- answered
- rejected
- errored

No silent disappearance.

## Stage 9: Render inspection bundle

Per-course YAML should include:
- normalized course
- extracted topics
- canonical topics
- question candidates
- repairs/rejections
- answers
- final rows
- summary stats

## Suggested evaluation metrics

### Topic extraction
- atomic topic precision
- atomic topic recall
- broad-heading leakage rate
- compound-topic split rate

### Question generation
- sensible question rate
- duplicate intent rate
- reject rate
- entry-question coverage per topic

### Answer stage
- grounded answer rate
- uncertain rate
- false-confidence rate

## v1 non-requirements

Do not build these first:
- personalization
- speculative serving
- graph database dependency
- adaptive tutoring runtime
- large ontology systems
