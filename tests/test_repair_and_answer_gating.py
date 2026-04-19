from __future__ import annotations

from course_pipeline.schemas import QuestionCandidate
from course_pipeline.tasks.repair_questions import repair_or_reject_questions


def _candidate(candidate_id: str, text: str, family: str = "purpose") -> QuestionCandidate:
    return QuestionCandidate(
        candidate_id=candidate_id,
        relevant_topics=["correlation"],
        family=family,
        pattern=text,
        question_text=text,
    )

def test_repair_does_not_downgrade_why_do_we_use() -> None:
    repairs = repair_or_reject_questions([_candidate("q1", "Why do we use correlation?")])

    assert repairs[0].status == "accepted"
    assert repairs[0].final_text == "Why do we use correlation?"


def test_ungrammatical_why_does_is_rejected() -> None:
    repairs = repair_or_reject_questions([_candidate("q1", "Why does correlation?")])

    assert repairs[0].status == "rejected"
    assert repairs[0].reject_reason == "malformed"
