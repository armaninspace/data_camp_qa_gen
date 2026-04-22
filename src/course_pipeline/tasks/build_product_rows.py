from __future__ import annotations

import re

from course_pipeline.schemas import CacheRow, SyntheticAnswerDraft, TrainRow


def build_train_rows(
    answer_drafts: list[SyntheticAnswerDraft],
    question_variants_by_question_id: dict[str, list[str]] | None = None,
) -> list[TrainRow]:
    question_variants_by_question_id = question_variants_by_question_id or {}
    rows: list[TrainRow] = []
    for index, answer in enumerate(answer_drafts, start=1):
        variants = question_variants_by_question_id.get(
            answer.question_id,
            [answer.question_text],
        )
        train_eligible = bool(answer.answer_text.strip()) and not answer.off_topic
        cache_eligible = train_eligible
        rows.append(
            TrainRow(
                row_id=f"{answer.course_id}:{answer.question_id}:a:{index}",
                course_id=answer.course_id,
                question_id=answer.question_id,
                question_text=answer.question_text,
                provided_context=answer.provided_context,
                answer_text=answer.answer_text,
                question_variants=variants,
                answer_quality_flags={
                    "course_aligned": answer.course_aligned,
                    "weak_grounding": answer.weak_grounding,
                    "off_topic": answer.off_topic,
                    "duplicate_signature": _global_question_signature(answer.question_text),
                    "train_eligible": train_eligible,
                    "cache_eligible": cache_eligible,
                    "needs_review": answer.needs_review,
                },
                global_question_signature=_global_question_signature(answer.question_text),
            )
        )
    return rows


def build_cache_rows(train_rows: list[TrainRow]) -> list[CacheRow]:
    cache_rows: list[CacheRow] = []
    for row in train_rows:
        if not row.answer_quality_flags.cache_eligible:
            continue
        cache_rows.append(
            CacheRow(
                cache_key=f"{row.course_id}::{_global_question_signature(row.question_text)}",
                course_id=row.course_id,
                question_text=row.question_text,
                question_variants=row.question_variants,
                provided_context=row.provided_context,
                canonical_answer=row.answer_text,
                cache_eligible=True,
                global_question_signature=row.global_question_signature,
                cross_course_similarity=row.cross_course_similarity,
            )
        )
    return cache_rows


def _global_question_signature(question_text: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s]", "", question_text.lower())
    return re.sub(r"\s+", " ", normalized).strip()
