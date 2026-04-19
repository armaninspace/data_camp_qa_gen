from __future__ import annotations

from course_pipeline.schemas import CanonicalTopic
from course_pipeline.tasks.generate_questions import generate_question_candidates


def _topic(label: str, topic_type: str, topic_id: str) -> CanonicalTopic:
    return CanonicalTopic(
        canonical_topic_id=topic_id,
        label=label,
        aliases=[label],
        member_topic_ids=[topic_id],
        topic_type=topic_type,
    )


def test_wrapper_topics_do_not_generate_standard_questions() -> None:
    topics = [_topic("case study", "case_study_container", "ct1")]

    candidates = generate_question_candidates(topics)

    assert candidates == []


def test_nonsense_comparison_is_blocked() -> None:
    topics = [
        _topic("programming with purrr", "concept", "ct1"),
        _topic("case study", "case_study_container", "ct2"),
    ]

    candidates = generate_question_candidates(topics)

    assert not any(candidate.family == "comparison" for candidate in candidates)


def test_related_topics_can_generate_comparison() -> None:
    topics = [
        _topic("correlation", "metric", "ct1"),
        _topic("autocorrelation", "metric", "ct2"),
    ]

    candidates = generate_question_candidates(topics)

    assert any(candidate.family == "comparison" for candidate in candidates)
