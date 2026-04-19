
from __future__ import annotations

from course_pipeline.schemas import QuestionCandidate, QuestionRepair


BAD_PATTERNS = {
    "common data problems",
    "advanced data problems",
    "categorical and text data",
}


def repair_or_reject_questions(
    candidates: list[QuestionCandidate],
) -> list[QuestionRepair]:
    repairs: list[QuestionRepair] = []
    seen: set[str] = set()

    for candidate in candidates:
        text = candidate.question_text.strip()
        low = text.lower()

        if any(bad in low for bad in BAD_PATTERNS):
            repairs.append(
                QuestionRepair(
                    candidate_id=candidate.candidate_id,
                    status="rejected",
                    original_text=text,
                    final_text=None,
                    reject_reason="broad_heading"
                    if "problems" in low
                    else "compound_topic",
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

        repaired = text.replace("Why do we use", "Why does").replace("  ", " ")
        status = "repaired" if repaired != text else "accepted"
        repairs.append(
            QuestionRepair(
                candidate_id=candidate.candidate_id,
                status=status,
                original_text=text,
                final_text=repaired,
                reject_reason=None,
            )
        )
    return repairs
