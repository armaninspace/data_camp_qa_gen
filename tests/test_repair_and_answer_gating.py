from __future__ import annotations

from course_pipeline.schemas import GeneratedQuestion, QuestionCandidate
from course_pipeline.tasks.repair_questions import repair_or_reject_questions, validate_questions


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


def _generated(question_id: str, text: str) -> GeneratedQuestion:
    return GeneratedQuestion(
        question_id=question_id,
        relevant_topics=["topic"],
        family="entry",
        pattern="What is {x}?",
        question_text=text,
        generation_scope="single_topic",
    )


def test_entry_question_with_course_preamble_topic_is_rejected() -> None:
    validations = validate_questions([_generated("q1", "What is intro to basics?")])

    assert validations[0].status == "rejected"
    assert validations[0].reject_reason == "course_preamble"


def test_entry_question_with_course_title_scope_topic_is_rejected() -> None:
    validations = validate_questions(
        [
            _generated("q1", "What is survival analysis in R?"),
            _generated("q2", "What is loading data in pandas?"),
        ]
    )

    assert validations[0].status == "rejected"
    assert validations[0].reject_reason == "course_title_scope"
    assert validations[1].status == "rejected"
    assert validations[1].reject_reason == "course_preamble"


def test_exact_junk_entry_questions_are_rejected_before_answer_synthesis() -> None:
    validations = validate_questions(
        [
            _generated("q1", "What is getting started in python?"),
            _generated("q2", "What is different types of plots?"),
            _generated("q3", "What is where?"),
        ]
    )

    assert [item.status for item in validations] == ["rejected", "rejected", "rejected"]
    assert validations[0].reject_reason == "course_preamble"
    assert validations[1].reject_reason == "course_preamble"
    assert validations[2].reject_reason == "sql_keyword_fragment"


def test_positive_control_entry_questions_stay_accepted() -> None:
    validations = validate_questions(
        [
            _generated("q1", "What is matplotlib?"),
            _generated("q2", "What is pandas?"),
            _generated("q3", "What is dictionary?"),
            _generated("q4", "What is control flow?"),
        ]
    )

    assert all(item.status == "accepted" for item in validations)
    assert all(item.reject_reason is None for item in validations)
