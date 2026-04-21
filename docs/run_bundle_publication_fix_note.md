# Run and Bundle Publication Fix Note

## What was wrong

The publication layer could mix incompatible selection scopes.

A filtered inspection bundle was being built by filtering each artifact
independently, mostly by course id only. That allowed exported flat files to
drift from the declared bundle selection and from each other.

Separately, published `data/final/run_summary.yaml` could report zero LLM usage
because publish rebuilt the summary from `data/final` without carrying forward
the run's `logs/llm_calls.jsonl`.

## What was changed

### 1. Canonical bundle selection

Bundle creation now builds one canonical selection object first and uses it for
every exported artifact.

The selection includes:

- `bundle_id`
- `source_run_id`
- `export_mode`
- `selected_course_ids`
- `selected_question_ids`
- `selected_row_ids`

Additional artifact-specific ids such as train-row ids and cache keys are also
captured so the bundle export can be validated deterministically.

### 2. Bundle validation

Bundle creation now writes:

- `bundle_validation.json`

It records expected vs observed course ids, row counts, missing ids, unexpected
ids, and overall pass/fail status.

If validation fails, bundle creation fails.

### 3. Clear run-level vs bundle-level truth

Inside a filtered bundle:

- `run_summary.yaml` is now the bundle-level filtered summary
- `source_run_summary.yaml` preserves the full source-run summary

That prevents silent mixing of full-run summary data with filtered bundle
artifacts.

### 4. Published LLM observability

Publish now propagates:

- `logs/llm_calls.jsonl`
- `logs/pricing_snapshot.json`

into `data/final`, so rebuilt published summaries report real LLM call counts,
tokens, and cost instead of zero.

## Result

The publication path is now stricter:

- a bundle must match one canonical selection
- a filtered bundle cannot mix course sets across artifacts
- published run summaries preserve LLM usage accounting

