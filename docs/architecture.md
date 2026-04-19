
# Architecture Notes

## Orchestration

Use Prefect.

Main flow:
- `course_question_pipeline_flow`

Tasks:
1. `load_course_records`
2. `normalize_course`
3. `extract_atomic_topics`
4. `canonicalize_topics`
5. `generate_question_candidates`
6. `repair_or_reject_questions`
7. `answer_questions`
8. `build_ledger_rows`
9. `render_course_bundle`
10. `render_run_summary`

## Storage model

Start file-first.

Run directory:
```text
data/pipeline_runs/<run_id>/
  normalized_courses.jsonl
  topics.jsonl
  question_candidates.jsonl
  question_repairs.jsonl
  answers.jsonl
  all_rows.jsonl
  run_summary.yaml
  course_yaml/
    <course_id>.yaml
```

## Why file-first

- easy to diff
- easy to inspect
- easy to hand to humans
- lower operational cost early on

Optional later:
- Postgres
- pgvector

## Prompt architecture

Prompt A:
- extract atomic topics

Prompt B:
- expand questions from pattern bank

Prompt C:
- repair or reject

Prompt D:
- answer and rate correctness

## Suggested model use

`gpt-5.4`
- topic extraction
- repair/reject
- answer correctness

`gpt-5.1-mini`
- question expansion
- cheap large-batch generation

## Debugging philosophy

The easiest failure diagnosis should be:

- topic missing
- question generated badly
- question rejected
- answer unsupported

If the system makes that hard, simplify the design.
