from __future__ import annotations

from itertools import combinations

from course_pipeline.pattern_bank import PATTERN_BANK, TOPIC_TYPE_FAMILIES
from course_pipeline.schemas import CanonicalTopic, QuestionCandidate


GENERIC_COMPARE_STOPWORDS = {
    "data",
    "model",
    "models",
    "code",
    "time",
}


def generate_question_candidates(
    canonical_topics: list[CanonicalTopic],
) -> list[QuestionCandidate]:
    candidates: list[QuestionCandidate] = []

    for topic in canonical_topics:
        families = TOPIC_TYPE_FAMILIES.get(topic.topic_type, ["entry"])
        for family in families:
            patterns = PATTERN_BANK.get(family, [])
            for pattern in patterns[:1]:
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

    for left, right in combinations(canonical_topics[:12], 2):
        if not _topics_related_enough(left, right):
            continue
        pattern = PATTERN_BANK["comparison"][0]
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


def _topics_related_enough(left: CanonicalTopic, right: CanonicalTopic) -> bool:
    disallowed_types = {"chapter_wrapper", "example_block", "case_study_container"}
    if left.topic_type in disallowed_types or right.topic_type in disallowed_types:
        return False

    left_label = left.label.lower()
    right_label = right.label.lower()
    if left_label == right_label:
        return False
    if left_label in right_label or right_label in left_label:
        return True

    left_tokens = {
        token for token in left_label.replace("-", " ").split() if token not in GENERIC_COMPARE_STOPWORDS
    }
    right_tokens = {
        token for token in right_label.replace("-", " ").split() if token not in GENERIC_COMPARE_STOPWORDS
    }
    if left_tokens & right_tokens:
        return True

    return False
