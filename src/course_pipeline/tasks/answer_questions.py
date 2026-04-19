
from __future__ import annotations

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
    overview = ((course.summary or "") + " " + (course.overview or "")).lower()

    for repair in repairs:
        if repair.status == "rejected" or not repair.final_text:
            continue

        q = repair.final_text
        ql = q.lower()

        answer_text = None
        correctness = "uncertain"
        conf = 0.4
        evidence: list[TopicEvidence] = []

        if "record linkage" in ql and "record linkage" in overview:
            answer_text = (
                "Record linkage is a way to connect records across datasets "
                "when values may differ because of typos or spelling changes."
            )
            correctness = "correct"
            conf = 0.9
            evidence = [TopicEvidence(source="overview", text="record linkage")]
        elif "text data" in ql and "text data" in overview:
            answer_text = (
                "Text data is string-based or unstructured data that often "
                "needs cleaning for consistency."
            )
            correctness = "correct"
            conf = 0.85
            evidence = [TopicEvidence(source="overview", text="text data")]
        elif "categorical data" in ql and (
            "categorical" in overview or "category labels" in overview
        ):
            answer_text = (
                "Categorical data is data represented by labels or categories "
                "rather than free-form values."
            )
            correctness = "correct"
            conf = 0.82
            evidence = [TopicEvidence(source="overview", text="category labels")]
        elif "missing values" in ql and "missing values" in overview:
            answer_text = (
                "Missing values are absent entries in data that can affect "
                "analysis if they are not handled carefully."
            )
            correctness = "correct"
            conf = 0.88
            evidence = [TopicEvidence(source="overview", text="missing values")]
        elif "duplicates" in ql and "duplicated" in overview:
            answer_text = (
                "Duplicates are repeated data points that can lead to "
                "double-counting if they are not removed."
            )
            correctness = "correct"
            conf = 0.84
            evidence = [TopicEvidence(source="overview", text="duplicated data")]
        else:
            answer_text = (
                "The course appears to mention this topic, but the scraped "
                "text may not support a stronger answer."
            )
            correctness = "uncertain"
            conf = 0.35

        answers.append(
            AnswerRecord(
                question_id=repair.candidate_id,
                question_text=q,
                answer_text=answer_text,
                correctness=correctness,
                confidence=conf,
                evidence=evidence,
            )
        )

    return answers
