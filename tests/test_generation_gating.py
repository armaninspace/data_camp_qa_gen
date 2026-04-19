from __future__ import annotations

from course_pipeline.schemas import CanonicalTopic, VettedTopic, VettedTopicPair
from course_pipeline.tasks.generate_questions import (
    generate_pairwise_questions,
    generate_question_candidates,
    generate_single_topic_questions,
)


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


def test_rejected_vetted_topic_does_not_generate_single_topic_questions() -> None:
    topics = [
        VettedTopic(
            canonical_topic_id="ct1",
            canonical_label="case study",
            decision="reject",
            allow_single_topic_questions=False,
            allow_pairwise_questions=False,
            reason="wrapper_or_heading_like_topic",
            final_topic_type="case_study_container",
        )
    ]

    questions = generate_single_topic_questions(topics)

    assert questions == []


def test_only_kept_pairs_generate_pairwise_questions() -> None:
    pairs = [
        VettedTopicPair(
            pair_id="p1",
            topic_x="categorical data",
            topic_y="text data",
            decision="keep_pair",
            reason="paired_scope_supported",
        ),
        VettedTopicPair(
            pair_id="p2",
            topic_x="correlation",
            topic_y="case study",
            decision="reject_pair",
            reason="topic_rejected",
        ),
    ]

    questions = generate_pairwise_questions(pairs)

    assert len(questions) == 1
    assert questions[0].relevant_topics == ["categorical data", "text data"]
