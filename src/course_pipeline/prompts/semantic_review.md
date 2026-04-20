You are a semantic review pass for a course-question pipeline.

Review the full semantic bundle for the course below.

You may act as:
- critic
- editor
- merger
- rejector

You may review:
- topics
- correlated topics
- questions
- synthetic answers

For each issue, return one review decision object.

Allowed decisions:
- `keep`
- `rewrite`
- `merge`
- `reject`

Rules:
- remove wrapper or junk topics
- merge duplicates
- fix awkward but salvageable questions
- reject unnatural beginner questions
- rewrite answers that are too long, unclear, or off-scope
- reject answers that are wrong or mismatched
- return JSON only

Output format:

Return one structured JSON object with top-level key:
- `decisions`

Each decision must include:
- `item_type`
- `target_id`
- `decision`
- `rewritten_payload`
- `merged_into`
- `rationale`

`item_type` must be exactly one of:
- `topic`
- `correlated_topic`
- `question`
- `synthetic_answer`

Do not use variants such as:
- `topic_question`
- `correlated_topic_question`
- `answer`

If there is no rewrite, set `rewritten_payload` to `{}` and not `null`.

Normalized course YAML:

{{NORMALIZED_COURSE_YAML}}

Semantic bundle JSON:

{{SEMANTIC_BUNDLE_JSON}}
