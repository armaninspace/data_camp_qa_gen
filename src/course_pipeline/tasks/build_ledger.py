
from __future__ import annotations

from course_pipeline.schemas import (
    AnswerRecord,
    LedgerRow,
    NormalizedCourse,
    QuestionCandidate,
    QuestionRepair,
)


def build_ledger_rows(
    course: NormalizedCourse,
    candidates: list[QuestionCandidate],
    repairs: list[QuestionRepair],
    answers: list[AnswerRecord],
) -> list[LedgerRow]:
    answer_by_id = {a.question_id: a for a in answers}
    cand_by_id = {c.candidate_id: c for c in candidates}
    rows: list[LedgerRow] = []

    for repair in repairs:
        candidate = cand_by_id[repair.candidate_id]
        answer = answer_by_id.get(repair.candidate_id)

        if repair.status == "rejected":
            rows.append(
                LedgerRow(
                    row_id=f"r_{len(rows)+1:06d}",
                    course={
                        "course_id": course.course_id,
                        "title": course.title,
                    },
                    relevant_topics=candidate.relevant_topics,
                    question_text=repair.original_text,
                    question_answer=None,
                    correctness=None,
                    question_family=candidate.family,
                    status="rejected",
                    reject_reason=repair.reject_reason,
                    source_evidence=[],
                )
            )
            continue

        if answer is None:
            rows.append(
                LedgerRow(
                    row_id=f"r_{len(rows)+1:06d}",
                    course={
                        "course_id": course.course_id,
                        "title": course.title,
                    },
                    relevant_topics=candidate.relevant_topics,
                    question_text=repair.final_text or repair.original_text,
                    question_answer=None,
                    correctness=None,
                    question_family=candidate.family,
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
                relevant_topics=candidate.relevant_topics,
                question_text=answer.question_text,
                question_answer=answer.answer_text,
                correctness=answer.correctness,
                question_family=candidate.family,
                status="answered",
                reject_reason=None,
                source_evidence=answer.evidence,
            )
        )

    return rows
