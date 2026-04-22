from __future__ import annotations

from course_pipeline.schemas import (
    AnswerRecord,
    GeneratedQuestion,
    NormalizedCourse,
    QuestionValidationRecord,
    TeacherAnswerDraft,
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


def _teacher_answer(*, off_topic: bool = False, answer_text: str = "Pandas is a Python library.") -> TeacherAnswerDraft:
    return TeacherAnswerDraft.model_validate(
        {
            "course_id": "24372",
            "question_id": "sq_001",
            "question_text": "What is pandas?",
            "provided_context": {
                "course_context_frame": {
                    "course_id": "24372",
                    "course_title": "Intermediate Python",
                    "learner_level": "beginner",
                    "domain": "python",
                    "primary_tools": ["pandas"],
                    "core_tasks": ["tabular analysis"],
                    "scope_bias": [],
                    "answer_style": {
                        "depth": "introductory",
                        "tone": "direct",
                        "prefer_examples": True,
                        "prefer_definitions": True,
                        "keep_short": True,
                    },
                },
                "question_context_frame": {
                    "question_id": "sq_001",
                    "course_id": "24372",
                    "question_text": "What is pandas?",
                    "question_intent": "definition",
                    "relevant_topics": ["pandas"],
                    "chapter_scope": [],
                    "expected_answer_shape": ["short definition"],
                    "scope_bias": [],
                    "support_refs": [],
                },
            },
            "teacher_answer": answer_text,
            "source_refs": ["summary", "overview"],
            "course_aligned": True,
            "weak_grounding": False,
            "off_topic": off_topic,
            "needs_review": False,
            "model_name": "gpt-5.4",
            "prompt_family": "teacher_answer",
        }
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
        [_teacher_answer(answer_text="Pandas is a teacher answer.")],
    )

    assert len(rows) == 1
    assert rows[0].status == "answered"
    assert rows[0].question_answer == "Pandas is an answer record."
    assert rows[0].source_refs == ["chapter:2"]


def test_build_ledger_rows_falls_back_to_teacher_answers() -> None:
    rows = build_ledger_rows(
        _course(),
        [_question()],
        [_validation()],
        [],
        [_teacher_answer()],
    )

    assert len(rows) == 1
    assert rows[0].status == "answered"
    assert rows[0].question_answer == "Pandas is a Python library."
    assert rows[0].correctness == "correct"
    assert rows[0].source_refs == ["summary", "overview"]


def test_build_ledger_rows_still_errors_when_teacher_answer_is_unusable() -> None:
    rows = build_ledger_rows(
        _course(),
        [_question()],
        [_validation()],
        [],
        [_teacher_answer(off_topic=True)],
    )

    assert len(rows) == 1
    assert rows[0].status == "errored"
    assert rows[0].reject_reason == "missing_answer"
