from __future__ import annotations

import re
from typing import Any

from course_pipeline.schemas import (
    CourseContextFrame,
    GeneratedQuestion,
    NormalizedCourse,
    QuestionContextFrame,
    QuestionIntent,
    SemanticQuestion,
)


QUESTION_INTENT_BY_FAMILY = {
    "what_is": "definition",
    "why_is": "purpose",
    "when_to_use": "decision",
    "how_does_it_work": "procedure",
    "what_is_it_used_for": "usage",
    "how_are_x_and_y_related": "relationship",
    "what_is_the_difference_between_x_and_y": "comparison",
    "why_are_x_and_y_often_used_together": "relationship",
    "when_would_you_use_x_instead_of_y": "comparison",
}
EXPECTED_ANSWER_SHAPES = {
    "definition": [
        "short definition",
        "why it matters in this course",
        "one simple example",
    ],
    "purpose": [
        "direct reason",
        "why it matters in this course",
        "one simple example",
    ],
    "usage": [
        "direct use case",
        "why it matters in this course",
        "one simple example",
    ],
    "comparison": [
        "key difference",
        "when to use each",
        "one brief contrast",
    ],
    "relationship": [
        "short relationship statement",
        "how they fit together in this course",
        "one simple example",
    ],
    "procedure": [
        "short procedural explanation",
        "main steps or mechanism",
        "one simple example",
    ],
    "decision": [
        "decision rule",
        "course-relevant tradeoff",
        "one simple example",
    ],
}


def build_question_context_frame(
    *,
    course: NormalizedCourse,
    question: SemanticQuestion | GeneratedQuestion | dict[str, Any],
    course_context_frame: CourseContextFrame,
) -> QuestionContextFrame:
    payload = _question_payload(question)
    intent = _infer_question_intent(payload)
    return QuestionContextFrame(
        question_id=str(payload["question_id"]),
        course_id=course.course_id,
        question_text=str(payload["question_text"]),
        question_intent=intent,
        relevant_topics=[str(item) for item in payload.get("relevant_topics", [])],
        chapter_scope=_infer_chapter_scope(course, payload),
        expected_answer_shape=_expected_answer_shape(intent),
        scope_bias=_infer_scope_bias(course_context_frame, intent),
        support_refs=_infer_support_refs(course, payload),
    )


def build_question_context_frames(
    *,
    course: NormalizedCourse,
    questions: list[SemanticQuestion | GeneratedQuestion | dict[str, Any]],
    course_context_frame: CourseContextFrame,
) -> list[QuestionContextFrame]:
    return [
        build_question_context_frame(
            course=course,
            question=question,
            course_context_frame=course_context_frame,
        )
        for question in questions
    ]


def _question_payload(question: SemanticQuestion | GeneratedQuestion | dict[str, Any]) -> dict[str, Any]:
    if hasattr(question, "model_dump"):
        return question.model_dump(mode="json")
    return dict(question)


def _infer_question_intent(payload: dict[str, Any]) -> QuestionIntent:
    family = str(payload.get("question_family") or payload.get("family") or "").strip()
    if family in QUESTION_INTENT_BY_FAMILY:
        return QUESTION_INTENT_BY_FAMILY[family]  # type: ignore[return-value]

    question_text = str(payload.get("question_text") or "").strip().lower()
    if question_text.startswith("what is"):
        return "definition"
    if question_text.startswith("why"):
        return "purpose"
    if question_text.startswith("when"):
        return "decision"
    if question_text.startswith("how"):
        return "procedure"
    return "other"


def _infer_chapter_scope(course: NormalizedCourse, payload: dict[str, Any]) -> list[str]:
    refs = {str(item).strip().lower() for item in payload.get("source_refs", [])}
    relevant_topics = [str(item).strip().lower() for item in payload.get("relevant_topics", [])]
    matched: list[str] = []
    for chapter in course.chapters:
        chapter_ref = f"chapter:{chapter.chapter_index}"
        haystack = " ".join(filter(None, [chapter.title, chapter.summary or ""])).lower()
        if chapter_ref in refs:
            matched.append(chapter.title)
            continue
        if any(topic and topic in haystack for topic in relevant_topics):
            matched.append(chapter.title)
    return list(dict.fromkeys(matched))


def _expected_answer_shape(intent: QuestionIntent) -> list[str]:
    return EXPECTED_ANSWER_SHAPES.get(intent, ["short answer", "course-relevant framing"])


def _infer_scope_bias(
    course_context_frame: CourseContextFrame,
    intent: QuestionIntent,
) -> list[str]:
    bias = list(course_context_frame.scope_bias)
    if intent == "definition":
        bias.append("prefer a short definition first")
    elif intent == "comparison":
        bias.append("focus on contrast rather than full surveys")
    elif intent == "relationship":
        bias.append("explain how the concepts connect in this course")
    elif intent == "usage":
        bias.append("focus on course-relevant usage")
    return list(dict.fromkeys(bias))


def _infer_support_refs(course: NormalizedCourse, payload: dict[str, Any]) -> list[str]:
    refs = [str(item) for item in payload.get("source_refs", []) if str(item).strip()]
    if course.summary:
        refs.append("summary")
    if course.overview:
        refs.append("overview")
    refs.extend(
        f"chapter_{chapter.chapter_index}"
        for chapter in course.chapters
        if chapter.title in _infer_chapter_scope(course, payload)
    )
    return list(dict.fromkeys(refs))
