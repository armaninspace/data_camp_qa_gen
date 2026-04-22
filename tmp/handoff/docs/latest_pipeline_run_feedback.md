# Feedback on Latest New-Pipeline Run

## Bottom Line

This run is a **product-shape improvement** and an **operational reliability problem**.

The pipeline is now producing the kinds of artifacts we actually want:

- `train_rows.jsonl`
- `cache_rows.jsonl`
- `provided_context`
- `course_context_frame`
- `question_context_frame`
- teacher answers

That is real progress.

But the run is still dropping too many answers between teacher-answer generation and final row materialization.

## Headline Assessment

### What improved

- The pipeline is now centered much more clearly around cache/training outputs.
- Same-looking questions are being kept separate across courses.
- Teacher answers are being generated broadly enough that the main problem is no longer raw answer generation.
- The new context-carrying shape is visible in the artifacts.

### What regressed or is still weak

- Final answer completion is too low.
- Too many final rows are ending up as `missing_answer`.
- Question-local context is often thin even when course-level context exists.
- Quality flags are too permissive to be useful.
- Final answers still lack meaningful evidence/source attachment.

## Current Performance Read

Based on the uploaded flat artifacts:

- **112 train rows**
- **112 cache rows**
- **112 total final rows**
- **84 answered**
- **28 errored**
- **0 rejected**

This implies:

- **Answer completion rate:** 75%
- **Error rate:** 25%

That is too weak for a pipeline whose main purpose is to create reusable cache rows and training rows.

## Most Important Finding

The main problem is **not answer generation**.

The main problem is **answer propagation / answer attachment / final row assembly**.

In many cases, the pipeline appears to successfully generate a teacher answer in `train_rows`, but the corresponding final row still ends up as:

- `status: errored`
- `reject_reason: missing_answer`

That means the likely failure is in one of these places:

1. row joining / key matching
2. post-review answer propagation
3. answer serialization into final outputs
4. mismatch between train/cache rows and final row assembly

This is actually good news in one sense: the system is no longer primarily blocked on "can the model answer the question?" It is now primarily blocked on "can the pipeline consistently preserve and materialize the generated answer?"

## What Looks Good

### 1. Product contract is moving in the right direction

The run now emits the right families of artifacts for the intended use case.

That means the architecture is getting closer to:

`normalized course -> context frames -> questions -> teacher answers -> train rows -> cache rows`

rather than the older review-heavy / inspection-heavy shape.

### 2. Per-course separation is working

Same-looking questions are being preserved as separate rows across courses.

That is correct and should remain true.

We should not collapse same-looking questions across courses into one final answer, because the course framing, level, and intended answer style differ.

### 3. Teacher-answer generation is broad enough

The system appears capable of generating many plausible teacher answers.

That suggests the bottleneck has moved downstream.

## What Looks Weak

### 1. Final row completion is too low

A 75% answered rate is not good enough for a pipeline that is supposed to create reusable products.

This is the most urgent operational issue.

### 2. `question_context_frame` is underfilled

The course-level context exists and is often usable.

But the local question context is often too thin, with fields like:

- `relevant_topics: []`
- `chapter_scope: []`

That weakens the conditioning signal for small-model training.

### 3. Quality flags are not doing enough work

The new flags exist, but they appear too permissive.

If everything is effectively marked eligible, then the flags are not helping differentiate:

- high-confidence cache rows
- weaker-but-usable training rows
- questionable rows needing review

### 4. Evidence is still missing

Even where answers exist, the final artifacts still do not carry enough evidence or source linkage.

That makes the outputs weaker for inspection and less safe for direct serving.

## Interpretation

This run is best understood as:

- **an architectural win**
- **a data-product quality partial win**
- **an operational assembly failure**

The pipeline is closer to the thing we actually want to build.

But it is not yet doing a reliable job of turning generated answers into consistent final rows.

## Recommended Priority Fixes

### Priority 1: Make `train_rows` the answer source of truth

If a teacher answer exists in `train_rows`, the final pipeline should default to carrying it into the final row unless there is a clear blocking reason.

Do not let answers disappear silently.

### Priority 2: Debug answer attachment

Investigate the exact path from:

- generated teacher answer
- reviewed teacher answer
- final answered row

Find where `missing_answer` is being introduced despite teacher-answer presence.

### Priority 3: Strengthen `question_context_frame`

Ensure question-local frames consistently include:

- `relevant_topics`
- `chapter_scope`
- `question_intent`
- `expected_answer_shape`
- `support_refs`

Right now the model is still doing too much work from the naked question plus course frame.

### Priority 4: Make eligibility flags meaningful

Separate:

- `train_eligible`
- `cache_eligible`
- `needs_review`
- `weak_grounding`
- `off_topic`

These should be discriminative, not default-true.

### Priority 5: Attach lightweight evidence/source refs

Even a minimal source-linkage layer would be a big improvement.

The final row should carry at least enough source reference to explain why the answer belongs to the course.

## Policy Guidance Reinforced by This Run

### 1. Correct Q/A pairs should not be rejected just because they are generic

If the question-answer pair is correct and course-relevant, keep it.

Use flags, rewrites, or cache-vs-train separation instead of hard rejection whenever possible.

### 2. Same-looking questions across courses should remain separate

This run reinforces that requirement.

Course context matters.

### 3. Context frames should be optimized for small-model conditioning, not prose summary

The course and question context artifacts should be compact, structured, and machine-usable.

They are not human-readable blurbs. They are provided context for teacher generation and small-model training.

## Final Verdict

The latest run shows that we are **closer to the right product**, but **not yet at a reliable pipeline**.

The key shift is:

- old problem: semantic generation quality
- new dominant problem: pipeline consistency and answer propagation

That is progress.

But until answer completion climbs substantially above 75%, the pipeline is still underperforming for the actual goal of producing dependable cache rows and training rows.
