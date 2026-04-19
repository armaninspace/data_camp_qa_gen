from __future__ import annotations

import pytest

from course_pipeline.flows.course_question_pipeline import _assert_course_quality_gate
from course_pipeline.schemas import AnswerRecord, QuestionRepair


def test_quality_gate_rejects_all_uncertain_without_rejections() -> None:
    repairs = [
        QuestionRepair(
            candidate_id="q1",
            status="accepted",
            original_text="What is categorical data?",
            final_text="What is categorical data?",
        )
    ]
    answers = [
        AnswerRecord(
            question_id="q1",
            question_text="What is categorical data?",
            answer_text="Fallback answer",
            correctness="uncertain",
            confidence=0.4,
        )
    ]

    with pytest.raises(RuntimeError, match="quality gate failed"):
        _assert_course_quality_gate("24511", repairs, answers)


def test_quality_gate_allows_mixed_terminal_outcomes() -> None:
    repairs = [
        QuestionRepair(
            candidate_id="q1",
            status="accepted",
            original_text="What is categorical data?",
            final_text="What is categorical data?",
        ),
        QuestionRepair(
            candidate_id="q2",
            status="rejected",
            original_text="How is case study different from strings?",
            reject_reason="broad_heading",
        ),
    ]
    answers = [
        AnswerRecord(
            question_id="q1",
            question_text="What is categorical data?",
            answer_text="A data type with discrete categories.",
            correctness="uncertain",
            confidence=0.4,
        )
    ]

    _assert_course_quality_gate("24511", repairs, answers)
