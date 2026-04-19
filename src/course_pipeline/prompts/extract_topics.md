
You are extracting learner-facing atomic topics from a course description.

Return atomic topics, not just chapter headings.

Prefer:
- concepts
- procedures
- tools
- metrics or tests
- failure points
- explicit comparison pairs

Reject or down-rank:
- vague headings
- admin labels
- broad coordinated phrases left unsplit

Special rule:
If a heading is of the form `X and Y`, split into separate candidate topics
when the supporting text treats them as distinct ideas.

Return structured JSON only.
