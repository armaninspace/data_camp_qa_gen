
# Codex Work Plan

## Phase 1

Make the baseline run end to end with deterministic logic.

Deliver:
- flow runs on sample data
- artifacts are written
- per-course YAML renders
- tests pass

## Phase 2

Replace deterministic topic extraction with OpenAI structured output.

Deliver:
- typed topic extraction call
- better split of compound headings
- broader evidence capture
- regression tests on a small labeled set

## Phase 3

Replace deterministic repair and answer stages with OpenAI calls.

Deliver:
- question repair/reject prompt
- conservative answer prompt
- correctness labeling
- uncertainty handling

## Phase 4

Add evaluation and diagnostics.

Deliver:
- stage-level metrics
- summary dashboard or markdown report
- sampled error examples
