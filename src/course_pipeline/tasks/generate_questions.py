from __future__ import annotations

from itertools import combinations

from course_pipeline.pattern_bank import PATTERN_BANK, TOPIC_TYPE_FAMILIES
from course_pipeline.schemas import (
    CanonicalTopic,
    GeneratedQuestion,
    QuestionCandidate,
    VettedTopic,
    VettedTopicPair,
)


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


def generate_single_topic_questions(
    vetted_topics: list[VettedTopic],
) -> list[GeneratedQuestion]:
    questions: list[GeneratedQuestion] = []
    for topic in vetted_topics:
        if not topic.allow_single_topic_questions or topic.decision == "reject":
            continue

        families = ["entry"]
        for family in families:
            patterns = PATTERN_BANK.get(family, [])
            if not patterns:
                continue
            pattern = patterns[0]
            questions.append(
                GeneratedQuestion(
                    question_id=f"q{len(questions)+1:04d}",
                    relevant_topics=[topic.canonical_label],
                    source_topic_ids=[topic.canonical_topic_id],
                    family=family,
                    pattern=pattern,
                    question_text=pattern.format(x=topic.canonical_label),
                    evidence_spans=topic.evidence_spans,
                    generation_scope="single_topic",
                )
            )
    return questions


def generate_pairwise_questions(
    vetted_pairs: list[VettedTopicPair],
) -> list[GeneratedQuestion]:
    questions: list[GeneratedQuestion] = []
    comparison_patterns = [
        "How is {x} different from {y}?",
        "How are {x} and {y} related?",
        "When would you use {x} instead of {y}?",
        "What are the tradeoffs between {x} and {y}?",
    ]

    for pair in vetted_pairs:
        if pair.decision != "keep_pair":
            continue
        if pair.relation_type not in {"paired_scope", "explicit_comparison"}:
            continue
        pattern = comparison_patterns[0]
        questions.append(
            GeneratedQuestion(
                question_id=f"q_pair_{len(questions)+1:04d}",
                relevant_topics=[pair.topic_x, pair.topic_y],
                source_pair_id=pair.pair_id,
                family="comparison",
                pattern=pattern,
                question_text=pattern.format(x=pair.topic_x, y=pair.topic_y),
                evidence_spans=pair.evidence_spans,
                generation_scope="pairwise",
            )
        )
    return questions


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
