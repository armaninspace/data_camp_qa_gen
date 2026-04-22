# Codex Guidance: Do Not Reject Correct Q/A Pairs

## Purpose

This is a policy change for the pipeline.

If a generated question/answer pair is correct and usable, it must **not** be rejected simply because it is:

- too generic
- too beginner-level
- broader than the course emphasis
- not the preferred pedagogical wording
- less specific than an alternative rewrite

Those issues may affect routing, flags, ranking, cache eligibility, or whether a rewrite is also generated. They must **not** cause destructive rejection of an otherwise correct row.

The system goal is to produce:

- `train_rows.jsonl`
- `cache_rows.jsonl`

This means retention is more important than aggressive editorial pruning.

---

## New Retention Policy

### Non-negotiable rule

If the answer is correct and the question is understandable, keep the row.

Do **not** reject a row only because it is:

- too introductory for an intermediate course
- too broad relative to the course framing
- generic rather than course-optimized
- weaker than a better rewritten version
- similar to another valid phrasing

Instead:

- keep it in `train_rows`
- optionally keep it in `cache_rows` if it passes stricter cache rules
- attach flags describing its weaknesses
- optionally generate a rewritten course-optimized companion row

### Hard rejection is now reserved for only these cases

A row may be hard rejected only if one or more of the following is true:

1. the answer is materially incorrect
2. the answer contradicts the source/course context in a meaningful way
3. the question is malformed or unintelligible
4. the row is clearly off-topic for the course
5. the answer is empty or unusable
6. the row is unsafe or policy-disallowed
7. the row is a true duplicate byte-for-byte and preserving both adds no training or cache value

If none of those are true, the row should be retained.

---

## Required Output Behavior

### `train_rows`

This is the broad retention set.

Include rows that are:

- correct
- understandable
- course-adjacent or course-aligned
- useful as teacher data

A row can be included in `train_rows` even if it is:

- generic
- weakly course-conditioned
- too basic for the nominal level
- not cache-worthy
- missing preferred phrasing

### `cache_rows`

This is the stricter runtime subset.

A row should be included in `cache_rows` only if it is:

- correct
- stable
- course-conditioned enough for reuse
- phrased clearly
- not likely to confuse runtime matching

A row can be excluded from `cache_rows` without being rejected from `train_rows`.

---

## Replace Rejection With Flags

When a row has quality issues but is still correct, do not reject it.

Attach flags such as:

- `too_generic=true`
- `too_introductory=true`
- `weak_course_specificity=true`
- `rewrite_recommended=true`
- `cache_eligible=false`
- `train_eligible=true`
- `duplicate_group_id=...`
- `variant_of_question_id=...`

These flags should drive downstream use, not deletion.

---

## Rewrites Must Be Additive, Not Destructive

If the system can produce a better course-specific rewrite, do that **in addition to** the original row.

Example:

Keep the original:
- `What is random number generation used for?`

Also allow a better course-specific rewrite:
- `How is random number generation used in Python simulations?`

Both rows may be useful:

- the original is useful teacher data and maybe a cache variant
- the rewrite is more course-optimized and may be preferred for cache

Do not delete the original just because the rewrite is better.

---

## Same Question Across Courses

If the same surface question appears in multiple courses, keep separate rows per course.

Examples:

- `What is pandas?` in Course A
- `What is pandas?` in Course B

These must remain separate final rows because the provided context and ideal answer can differ by course.

Optional cross-course grouping metadata is allowed, but never collapse final rows across courses.

---

## Required Schema Changes

Ensure the row schemas support retention-with-flags.

### Train row

Required fields:

- `row_id`
- `course_id`
- `question_id`
- `question_text`
- `teacher_answer`
- `provided_context`
- `train_eligible`
- `cache_eligible`
- `quality_flags`
- `duplicate_group_id` (optional)
- `variant_role` (optional: `original`, `rewrite`, `paraphrase`)
- `source_refs` (optional)

### Cache row

Required fields:

- `cache_key`
- `course_id`
- `question_text`
- `canonical_answer`
- `question_variants`
- `provided_context`
- `cache_eligible`
- `quality_flags`

---

## Review Stage Changes

The review stage must stop acting like an editorial gate that deletes correct rows.

### Old behavior to remove

Do not hard reject rows solely because they are:

- beginner-level in an intermediate course
- generic instead of course-specific
- broad rather than tightly scoped
- less pedagogically preferred than another candidate

### New review behavior

The review stage should do one of four things:

1. `keep`
2. `keep_with_flags`
3. `keep_and_add_rewrite`
4. `hard_reject`

`hard_reject` should be rare and only used for the strict cases listed above.

---

## Ranking Instead Of Pruning

If multiple correct rows compete, rank them instead of deleting them.

Use ranking signals such as:

- course specificity
- answer stability
- cache utility
- clarity
- pedagogical value

But keep the lower-ranked correct rows in `train_rows` unless they meet a true hard-reject condition.

---

## Implementation Instructions

1. Audit all places where review currently emits `decision = reject`.
2. For each rejection rule, reclassify it into one of:
   - hard reject
   - keep with flag
   - keep and add rewrite
3. Remove any logic that drops rows merely for:
   - `too basic`
   - `too generic`
   - `too broad`
   - `less preferred wording`
   - `course level mismatch` when answer remains correct
4. Ensure original rows survive when rewrites are created.
5. Ensure `train_rows.jsonl` preserves retained originals plus rewrites plus useful paraphrases.
6. Ensure `cache_rows.jsonl` is derived as a stricter subset, not by deleting rows upstream.
7. Add regression tests proving that correct-but-generic rows are retained.

---

## Required Regression Tests

Add tests for the following cases.

### Case 1: Correct but too basic
Input:
- intermediate course
- question: `What is pandas?`
- correct answer

Expected:
- row kept in `train_rows`
- may be `cache_eligible=false`
- may get `too_introductory=true`
- no hard rejection

### Case 2: Correct but generic, with better rewrite
Input:
- question: `What is random number generation used for?`
- correct answer
- improved rewrite available

Expected:
- original retained
- rewrite also retained
- rewrite may be preferred for cache
- no destructive replacement

### Case 3: Same surface question in multiple courses
Input:
- `What is pandas?` for two different courses

Expected:
- two final rows
- separate `course_id`
- separate `provided_context`
- optional shared signature only as metadata

### Case 4: Truly bad row
Input:
- malformed or factually wrong answer

Expected:
- hard rejection allowed

---

## Definition Of Done

This policy is implemented only when all of the following are true:

1. Correct Q/A pairs are no longer dropped merely for being generic or too basic.
2. Rewrites are additive rather than destructive.
3. `train_rows` is a broad retained superset.
4. `cache_rows` is a stricter subset.
5. Review decisions distinguish `keep_with_flags` from `hard_reject`.
6. Regression tests enforce the new retention policy.

