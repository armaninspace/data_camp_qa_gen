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
            continue

        answer_text = evidence[0].text
        answers.append(
            AnswerRecord(
                question_id=repair.candidate_id,
                question_text=repair.final_text,
                answer_text=answer_text,
                correctness="correct",
                confidence=0.7,
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
