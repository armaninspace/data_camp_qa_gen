from __future__ import annotations

from course_pipeline.schemas import (
    AnswerRecord,
    GeneratedQuestion,
    LedgerRow,
    NormalizedCourse,
    QuestionValidationRecord,
    TeacherAnswerDraft,
)


def build_ledger_rows(
    course: NormalizedCourse,
    questions: list[GeneratedQuestion],
    validations: list[QuestionValidationRecord],
    answers: list[AnswerRecord],
    teacher_answers: list[TeacherAnswerDraft] | None = None,
) -> list[LedgerRow]:
    answer_by_id = {answer.question_id: answer for answer in answers}
    teacher_answer_by_id = {
        answer.question_id: answer for answer in (teacher_answers or []) if answer.teacher_answer.strip()
    }
    question_by_id = {question.question_id: question for question in questions}
    rows: list[LedgerRow] = []

    for validation in validations:
        question = question_by_id[validation.question_id]
        answer = answer_by_id.get(validation.question_id)

        if validation.status == "rejected":
            rows.append(
                LedgerRow(
                    row_id=f"r_{len(rows)+1:06d}",
                    course={
                        "course_id": course.course_id,
                        "title": course.title,
                    },
                    relevant_topics=question.relevant_topics,
                    question_text=validation.original_text,
                    question_answer=None,
                    correctness=None,
                    question_family=question.family,
                    status="rejected",
                    reject_reason=validation.reject_reason,
                    source_evidence=[],
                )
            )
            continue

        if answer is None:
            teacher_answer = teacher_answer_by_id.get(validation.question_id)
            if teacher_answer is not None and not teacher_answer.off_topic:
                rows.append(
                    LedgerRow(
                        row_id=f"r_{len(rows)+1:06d}",
                        course={
                            "course_id": course.course_id,
                            "title": course.title,
                        },
                        relevant_topics=question.relevant_topics,
                        question_text=teacher_answer.question_text,
                        question_answer=teacher_answer.teacher_answer,
                        correctness="correct",
                        question_family=question.family,
                        status="answered",
                        reject_reason=None,
                        source_evidence=[],
                    )
                )
                continue
            rows.append(
                LedgerRow(
                    row_id=f"r_{len(rows)+1:06d}",
                    course={
                        "course_id": course.course_id,
                        "title": course.title,
                    },
                    relevant_topics=question.relevant_topics,
                    question_text=validation.final_text or validation.original_text,
                    question_answer=None,
                    correctness=None,
                    question_family=question.family,
                    status="errored",
                    reject_reason="missing_answer",
                    source_evidence=[],
                )
            )
            continue

        rows.append(
            LedgerRow(
                row_id=f"r_{len(rows)+1:06d}",
                course={
                    "course_id": course.course_id,
                    "title": course.title,
                },
                relevant_topics=question.relevant_topics,
                question_text=answer.question_text,
                question_answer=answer.answer_text,
                correctness=answer.correctness,
                question_family=question.family,
                status="answered",
                reject_reason=None,
                source_evidence=answer.evidence,
            )
        )

    return rows
