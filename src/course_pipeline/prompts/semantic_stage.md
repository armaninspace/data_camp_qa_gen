You are the semantic front end for a course-question pipeline.

Read the entire normalized course YAML below as one coherent object.

Your job is to return one structured JSON object with these top-level keys:
- `topics`
- `correlated_topics`
- `topic_questions`
- `correlated_topic_questions`
- `synthetic_answers`

Semantic requirements:
- identify real learner-facing topics
- identify heavily correlated topics
- generate only natural basic learner questions
- generate short synthetic tutor answers from general knowledge
- reject wrapper language, onboarding phrases, discourse fragments, narrative
  stray words, marketing phrases, and vague activity headings
- return JSON only

Prefer:
- concepts
- procedures
- tools
- metrics
- diagnostics
- tests
- natural beginner tutoring questions
- brief, clear, difficulty-matched answers

Avoid surfacing topics such as:
- `where`
- `getting started in python`
- `different types of plots`
- `learn to manipulate dataframes`

Recover learner-facing items such as:
- `pandas`
- `matplotlib`
- `dictionary`
- `control flow`
- `loop`
- `filtering`

Topic requirements:
- each topic must include:
  - `label`
  - `normalized_label`
  - `topic_type`
  - `confidence`
  - `course_centrality`
  - `source_refs`
  - `rationale`
  - optional `aliases`

Correlated-topic requirements:
- each correlated-topic record must include:
  - `topics`
  - `relationship_type`
  - `strength`
  - `rationale`

Topic-question requirements:
- allowed families:
  - `what_is`
  - `why_is`
  - `when_to_use`
  - `how_does_it_work`
  - `what_is_it_used_for`

Correlated-topic-question requirements:
- allowed families:
  - `how_are_x_and_y_related`
  - `what_is_the_difference_between_x_and_y`
  - `why_are_x_and_y_often_used_together`
  - `when_would_you_use_x_instead_of_y`

Synthetic-answer requirements:
- use general subject-matter knowledge
- do not quote brochure spans as the answer source
- keep answers brief, clear, and beginner-appropriate
- include:
  - `question_text`
  - `answer_text`
  - `answer_mode`
  - `difficulty_band`
  - `confidence`
  - `answer_rationale`
  - optional `related_topics`

Normalized course YAML:

{{NORMALIZED_COURSE_YAML}}
