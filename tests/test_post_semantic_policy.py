from __future__ import annotations

import pytest

from course_pipeline.schemas import GeneratedQuestion, NormalizedCourse, SemanticTopic
from course_pipeline.tasks.post_semantic_policy import (
    apply_post_semantic_policy,
    enforce_required_entry_coverage,
)


def _course() -> NormalizedCourse:
    return NormalizedCourse(
        course_id="7630",
        title="Introduction to R",
        metadata={"level": "Beginner"},
    )


def test_post_semantic_policy_maps_what_is_to_entry_and_marks_required_entries() -> None:
    questions = [
        GeneratedQuestion(
            question_id="sq_001",
            relevant_topics=["r"],
            source_refs=["overview"],
            family="what_is",
            pattern="semantic_stage",
            question_text="What is R?",
            generation_scope="single_topic",
        ),
        GeneratedQuestion(
            question_id="sq_002",
            relevant_topics=["factors"],
            source_refs=["chapter:4"],
            family="what_is",
            pattern="semantic_stage",
            question_text="What is a factor in R?",
            generation_scope="single_topic",
        ),
    ]
    semantic_topics = [
        SemanticTopic(
            label="R",
            normalized_label="r",
            topic_type="tool",
            confidence=0.99,
            course_centrality=1.0,
            source_refs=["overview"],
            rationale="Core tool.",
        ),
        SemanticTopic(
            label="Factors",
            normalized_label="factors",
            topic_type="concept",
            confidence=0.98,
            course_centrality=0.87,
            source_refs=["chapter:4"],
            rationale="Core concept.",
        ),
    ]

    updated_questions, report = apply_post_semantic_policy(
        course=_course(),
        semantic_topics=semantic_topics,
        questions=questions,
    )

    assert [question.family for question in updated_questions] == ["entry", "entry"]
    assert [question.required_entry for question in updated_questions] == [True, True]
    assert report.missing_anchors == []


def test_post_semantic_policy_reports_missing_anchor_when_no_entry_question_exists() -> None:
    questions = [
        GeneratedQuestion(
            question_id="sq_001",
            relevant_topics=["r"],
            source_refs=["overview"],
            family="why_is",
            pattern="semantic_stage",
            question_text="Why is R useful?",
            generation_scope="single_topic",
        )
    ]
    semantic_topics = [
        SemanticTopic(
            label="R",
            normalized_label="r",
            topic_type="tool",
            confidence=0.99,
            course_centrality=1.0,
            source_refs=["overview"],
            rationale="Core tool.",
        )
    ]

    _, report = apply_post_semantic_policy(
        course=_course(),
        semantic_topics=semantic_topics,
        questions=questions,
    )

    assert report.missing_anchors == ["r"]
    with pytest.raises(RuntimeError, match="required entry coverage missing for anchors: r"):
        enforce_required_entry_coverage(report)
