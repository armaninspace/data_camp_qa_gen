from __future__ import annotations

import re

from course_pipeline.schemas import (
    AnswerRecord,
    CanonicalTopic,
    NormalizedCourse,
    QuestionRepair,
    TopicEvidence,
)


def answer_questions(
    course: NormalizedCourse,
    canonical_topics: list[CanonicalTopic],
    repairs: list[QuestionRepair],
) -> list[AnswerRecord]:
    answers: list[AnswerRecord] = []
    support_spans = _support_spans(course)

    for repair in repairs:
        if repair.status == "rejected" or not repair.final_text:
            continue

        matched_topics = _matched_topics(repair.final_text, canonical_topics)
        if not matched_topics:
            continue

        evidence = _find_evidence(matched_topics, support_spans)
        if not evidence:
            evidence = _find_partial_evidence(matched_topics, support_spans)
        if not evidence:
            continue

        answer_text = evidence[0].text
        correctness = _classify_correctness(repair.final_text, evidence)
        answers.append(
            AnswerRecord(
                question_id=repair.candidate_id,
                question_text=repair.final_text,
                answer_text=answer_text,
                correctness=correctness,
                confidence=_confidence_for(correctness),
                evidence=evidence,
            )
        )

    return answers


def _support_spans(course: NormalizedCourse) -> list[TopicEvidence]:
    texts: list[tuple[str, str]] = []
    if course.summary:
        texts.append(("summary", course.summary))
    if course.overview:
        texts.append(("overview", course.overview))
    for chapter in course.chapters:
        texts.append((chapter.source, chapter.title))
        if chapter.summary:
            texts.append((chapter.source, chapter.summary))

    spans: list[TopicEvidence] = []
    for source, text in texts:
        for part in re.split(r"(?<=[.!?])\s+|\n+", text):
            clean = part.strip()
            if clean:
                spans.append(TopicEvidence(source=source, text=clean))
    return spans


def _matched_topics(
    question_text: str,
    canonical_topics: list[CanonicalTopic],
) -> list[str]:
    low = question_text.lower()
    matches: list[str] = []
    for topic in canonical_topics:
        if topic.label.lower() in low:
            matches.append(topic.label.lower())
    return matches


def _find_evidence(
    matched_topics: list[str],
    support_spans: list[TopicEvidence],
) -> list[TopicEvidence]:
    if len(matched_topics) > 1:
        for span in support_spans:
            span_low = span.text.lower()
            if all(topic in span_low for topic in matched_topics):
                return [span]
        return []

    target = matched_topics[0]
    for span in support_spans:
        if target in span.text.lower():
            return [span]
    return []


def _find_partial_evidence(
    matched_topics: list[str],
    support_spans: list[TopicEvidence],
) -> list[TopicEvidence]:
    for span in support_spans:
        span_low = span.text.lower()
        if any(topic in span_low for topic in matched_topics):
            return [span]
    return []


def _classify_correctness(
    question_text: str,
    evidence: list[TopicEvidence],
) -> str:
    question_low = question_text.lower()
    evidence_text = " ".join(item.text.lower() for item in evidence)

    if any(
        phrase in evidence_text
        for phrase in (
            "does not cover",
            "doesn't cover",
            "not covered",
            "not explained",
            "without discussing",
        )
    ):
        return "incorrect"

    if _is_weak_evidence(question_low, evidence):
        return "uncertain"

    return "correct"


def _is_weak_evidence(question_text: str, evidence: list[TopicEvidence]) -> bool:
    if not evidence:
        return True

    if any(item.source == "syllabus" for item in evidence):
        return True

    if any(len(item.text.split()) <= 5 for item in evidence):
        return True

    if question_text.startswith("how is ") and " different from " in question_text:
        return any(" and " not in item.text.lower() for item in evidence)

    return False


def _confidence_for(correctness: str) -> float:
    if correctness == "correct":
        return 0.7
    if correctness == "uncertain":
        return 0.4
    return 0.2
