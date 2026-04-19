from __future__ import annotations

import re

from course_pipeline.schemas import (
    GeneratedQuestion,
    QuestionCandidate,
    QuestionRepair,
    QuestionValidationRecord,
)


BAD_PATTERNS = {
    "common data problems",
    "advanced data problems",
    "categorical and text data",
    "case study",
    "putting it all together",
}


def repair_or_reject_questions(
    candidates: list[QuestionCandidate],
) -> list[QuestionRepair]:
    repairs: list[QuestionRepair] = []
    seen: set[str] = set()

    for candidate in candidates:
        text = _normalize_question(candidate.question_text)
        low = text.lower()

        if any(bad in low for bad in BAD_PATTERNS):
            repairs.append(
                QuestionRepair(
                    candidate_id=candidate.candidate_id,
                    status="rejected",
                    original_text=text,
                    final_text=None,
                    reject_reason="broad_heading"
                    if "problems" in low or "case study" in low or "putting it all together" in low
                    else "compound_topic",
                )
            )
            continue

        if _is_ungrammatical(text):
            repairs.append(
                QuestionRepair(
                    candidate_id=candidate.candidate_id,
                    status="rejected",
                    original_text=text,
                    final_text=None,
                    reject_reason="malformed",
                )
            )
            continue

        if text in seen:
            repairs.append(
                QuestionRepair(
                    candidate_id=candidate.candidate_id,
                    status="rejected",
                    original_text=text,
                    final_text=None,
                    reject_reason="duplicate_intent",
                )
            )
            continue
        seen.add(text)

        status = "accepted"
        repairs.append(
            QuestionRepair(
                candidate_id=candidate.candidate_id,
                status=status,
                original_text=candidate.question_text.strip(),
                final_text=text,
                reject_reason=None,
            )
        )
    return repairs


def validate_questions(
    questions: list[GeneratedQuestion],
) -> list[QuestionValidationRecord]:
    validations: list[QuestionValidationRecord] = []
    seen: set[str] = set()

    for question in questions:
        text = _normalize_question(question.question_text)
        low = text.lower()
        reject_reason: str | None = None
        status = "accepted"

        if question.generation_scope == "pairwise" and len(question.relevant_topics) != 2:
            reject_reason = "invalid_pair"
        elif any(bad in low for bad in BAD_PATTERNS):
            reject_reason = (
                "broad_heading"
                if "problems" in low or "case study" in low or "putting it all together" in low
                else "compound_topic"
            )
        elif _is_ungrammatical(text):
            reject_reason = "malformed"
        elif text in seen:
            reject_reason = "duplicate_intent"

        if reject_reason is not None:
            status = "rejected"
        else:
            seen.add(text)

        validations.append(
            QuestionValidationRecord(
                question_id=question.question_id,
                relevant_topics=question.relevant_topics,
                status=status,
                original_text=question.question_text.strip(),
                final_text=None if status == "rejected" else text,
                reject_reason=reject_reason,
                question_family=question.family,
                evidence_spans=question.evidence_spans,
            )
        )

    return validations


def _normalize_question(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if cleaned and not cleaned.endswith("?"):
        cleaned = f"{cleaned}?"
    return cleaned


def _is_ungrammatical(text: str) -> bool:
    low = text.lower()
    if re.search(r"\bwhy does [a-z0-9\- ]+\?$", low):
        return True
    if "??" in text:
        return True
    return False
