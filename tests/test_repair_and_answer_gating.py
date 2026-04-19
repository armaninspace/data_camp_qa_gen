from __future__ import annotations

from course_pipeline.schemas import CanonicalTopic, NormalizedCourse, QuestionCandidate
from course_pipeline.tasks.answer_questions import answer_questions
from course_pipeline.tasks.repair_questions import repair_or_reject_questions


def _candidate(candidate_id: str, text: str, family: str = "purpose") -> QuestionCandidate:
    return QuestionCandidate(
        candidate_id=candidate_id,
        relevant_topics=["correlation"],
        family=family,
        pattern=text,
        question_text=text,
    )


def _topic(label: str) -> CanonicalTopic:
    return CanonicalTopic(
        canonical_topic_id=f"ct_{label}",
        label=label,
        aliases=[label],
        member_topic_ids=[f"t_{label}"],
        topic_type="metric",
    )


def test_repair_does_not_downgrade_why_do_we_use() -> None:
    repairs = repair_or_reject_questions([_candidate("q1", "Why do we use correlation?")])

    assert repairs[0].status == "accepted"
    assert repairs[0].final_text == "Why do we use correlation?"


def test_ungrammatical_why_does_is_rejected() -> None:
    repairs = repair_or_reject_questions([_candidate("q1", "Why does correlation?")])

    assert repairs[0].status == "rejected"
    assert repairs[0].reject_reason == "malformed"


def test_answer_requires_evidence_span() -> None:
    course = NormalizedCourse(
        course_id="1",
        title="Example",
        overview="This course is about something else entirely.",
    )
    repairs = repair_or_reject_questions([_candidate("q1", "What is correlation?", family="entry")])

    answers = answer_questions(course, [_topic("correlation")], repairs)

    assert answers == []


def test_answer_uses_supporting_span() -> None:
    course = NormalizedCourse(
        course_id="1",
        title="Example",
        overview="Correlation describes the relationship between two time series.",
    )
    repairs = repair_or_reject_questions([_candidate("q1", "What is correlation?", family="entry")])

    answers = answer_questions(course, [_topic("correlation")], repairs)

    assert len(answers) == 1
    assert answers[0].evidence
    assert "Correlation describes" in answers[0].answer_text
    assert answers[0].correctness == "correct"


def test_answer_marks_heading_only_support_uncertain() -> None:
    course = NormalizedCourse(
        course_id="1",
        title="Example",
        chapters=[
            {
                "chapter_index": 1,
                "title": "Correlation",
                "summary": None,
                "source": "syllabus",
                "confidence": 1.0,
            }
        ],
    )
    repairs = repair_or_reject_questions([_candidate("q1", "What is correlation?", family="entry")])

    answers = answer_questions(course, [_topic("correlation")], repairs)

    assert len(answers) == 1
    assert answers[0].correctness == "uncertain"


def test_answer_marks_explicit_non_answer_incorrect() -> None:
    course = NormalizedCourse(
        course_id="1",
        title="Example",
        overview="This course does not cover how to use correlation in practice.",
    )
    repairs = repair_or_reject_questions(
        [_candidate("q1", "How do you use correlation?", family="procedure")]
    )

    answers = answer_questions(course, [_topic("correlation")], repairs)

    assert len(answers) == 1
    assert answers[0].correctness == "incorrect"
