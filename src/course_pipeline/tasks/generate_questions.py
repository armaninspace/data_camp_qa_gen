
from __future__ import annotations

from itertools import combinations
from course_pipeline.pattern_bank import PATTERN_BANK, TOPIC_TYPE_FAMILIES
from course_pipeline.schemas import CanonicalTopic, QuestionCandidate


def generate_question_candidates(
    canonical_topics: list[CanonicalTopic],
) -> list[QuestionCandidate]:
    candidates: list[QuestionCandidate] = []

    for topic in canonical_topics:
        families = TOPIC_TYPE_FAMILIES.get(topic.topic_type, ["entry"])
        for family in families:
            for pattern in PATTERN_BANK.get(family, [])[:2]:
                if "{y}" in pattern:
                    continue
                text = pattern.format(x=topic.label)
                candidates.append(
                    QuestionCandidate(
                        candidate_id=f"q{len(candidates)+1:04d}",
                        relevant_topics=[topic.label],
                        family=family,
                        pattern=pattern,
                        question_text=text,
                    )
                )

    for left, right in combinations(canonical_topics[:10], 2):
        for pattern in PATTERN_BANK["comparison"][:1]:
            candidates.append(
                QuestionCandidate(
                    candidate_id=f"q{len(candidates)+1:04d}",
                    relevant_topics=[left.label, right.label],
                    family="comparison",
                    pattern=pattern,
                    question_text=pattern.format(x=left.label, y=right.label),
                )
            )
    return candidates
