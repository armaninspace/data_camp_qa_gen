from __future__ import annotations

from course_pipeline.schemas import (
    AnswerRecord,
    GeneratedQuestion,
    NormalizedCourse,
    QuestionValidationRecord,
)
from course_pipeline.tasks.build_ledger import build_ledger_rows


def _course() -> NormalizedCourse:
    return NormalizedCourse(course_id="24372", title="Intermediate Python")


def _question() -> GeneratedQuestion:
    return GeneratedQuestion(
        question_id="sq_001",
        relevant_topics=["pandas"],
        family="what_is",
        pattern="semantic_stage",
        question_text="What is pandas?",
        generation_scope="single_topic",
    )


def _validation() -> QuestionValidationRecord:
    return QuestionValidationRecord(
        question_id="sq_001",
        relevant_topics=["pandas"],
        status="accepted",
        original_text="What is pandas?",
        final_text="What is pandas?",
        question_family="what_is",
    )


def test_build_ledger_rows_uses_answer_records_when_present() -> None:
    rows = build_ledger_rows(
        _course(),
        [_question()],
        [_validation()],
        [
            AnswerRecord(
                question_id="sq_001",
                question_text="What is pandas?",
                answer_text="Pandas is an answer record.",
                correctness="correct",
                source_refs=["chapter:2"],
            )
        ],
    )

    assert len(rows) == 1
    assert rows[0].status == "answered"
    assert rows[0].question_answer == "Pandas is an answer record."
    assert rows[0].source_refs == ["chapter:2"]


def test_build_ledger_rows_errors_when_answer_record_is_missing() -> None:
    rows = build_ledger_rows(
        _course(),
        [_question()],
        [_validation()],
        [],
    )

    assert len(rows) == 1
    assert rows[0].status == "errored"
    assert rows[0].reject_reason == "missing_answer"
