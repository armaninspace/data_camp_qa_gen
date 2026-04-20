from __future__ import annotations

from pathlib import Path
import time
import re

import yaml

from course_pipeline.llm import LLMClient
from course_pipeline.run_logging import RunLogger
from course_pipeline.schemas import NormalizedCourse, SemanticStageResult


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "semantic_stage.md"


def run_semantic_stage_for_course(
    *,
    course: NormalizedCourse | dict,
    llm_client: LLMClient,
    logger: RunLogger | None = None,
) -> SemanticStageResult:
    course_payload = (
        course.model_dump(mode="json") if hasattr(course, "model_dump") else dict(course)
    )
    prompt = _render_semantic_prompt(course_payload)

    started = time.perf_counter()
    semantic_json = llm_client.complete_json(prompt, "semantic_stage")
    latency_ms = int((time.perf_counter() - started) * 1000)

    course_id = str(course_payload["course_id"])
    if logger is not None:
        logger.log_llm_call(
            course_id=course_id,
            stage="semantic_stage",
            prompt_family="semantic_stage",
            configured_model=llm_client.model,
            requested_model=llm_client.model,
            actual_model=llm_client.model,
            actual_model_source="configured_model",
            provider_request_id=None,
            latency_ms=latency_ms,
            tokens_in=None,
            tokens_out=None,
            retry_count=0,
            status="success",
        )

    return SemanticStageResult.model_validate(
        _normalize_semantic_stage_payload(semantic_json)
    )


def _render_semantic_prompt(course_payload: dict) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    course_yaml = yaml.safe_dump(
        course_payload,
        sort_keys=False,
        allow_unicode=True,
        width=80,
    ).strip()
    return template.replace("{{NORMALIZED_COURSE_YAML}}", course_yaml)


def _normalize_semantic_stage_payload(payload: dict) -> dict:
    normalized = dict(payload)
    normalized["correlated_topics"] = _normalize_correlated_topics(
        payload.get("correlated_topics", [])
    )
    normalized["topic_questions"] = _normalize_question_items(
        payload.get("topic_questions", []),
        scope="single_topic",
        prefix="sq",
    )
    normalized["correlated_topic_questions"] = _normalize_question_items(
        payload.get("correlated_topic_questions", []),
        scope="correlated_topics",
        prefix="cq",
    )
    return normalized


def _normalize_correlated_topics(items: list[dict]) -> list[dict]:
    normalized_items: list[dict] = []
    for item in items:
        row = dict(item)
        topics = row.get("topics") or []
        if isinstance(topics, str):
            topics = [topics]
        row["topics"] = list(topics)
        row["relationship_type"] = _normalize_relationship_type(
            row.get("relationship_type")
        )
        row["rationale"] = row.get("rationale") or "normalized_from_semantic_stage_output"
        normalized_items.append(row)
    return normalized_items


def _normalize_question_items(
    items: list[dict],
    *,
    scope: str,
    prefix: str,
) -> list[dict]:
    normalized_items: list[dict] = []
    for index, item in enumerate(items, start=1):
        row = dict(item)
        topics = row.get("relevant_topics") or row.get("topics") or []
        if isinstance(topics, str):
            topics = [topics]
        question_text = str(row.get("question_text") or "").strip()
        row["relevant_topics"] = list(topics)
        row["question_scope"] = scope
        row["question_id"] = row.get("question_id") or f"{prefix}_{index:03d}"
        row["question_family"] = row.get("question_family") or _infer_question_family(
            question_text,
            scope=scope,
        )
        row["rationale"] = row.get("rationale") or "normalized_from_semantic_stage_output"
        row.setdefault("source_refs", [])
        normalized_items.append(row)
    return normalized_items


def _infer_question_family(question_text: str, *, scope: str) -> str:
    normalized = re.sub(r"\s+", " ", question_text.strip().lower())
    if scope == "correlated_topics":
        if normalized.startswith("how are "):
            return "how_are_x_and_y_related"
        if normalized.startswith("what is the difference between "):
            return "what_is_the_difference_between_x_and_y"
        if normalized.startswith("why are ") and "used together" in normalized:
            return "why_are_x_and_y_often_used_together"
        if normalized.startswith("when would you use ") and " instead of " in normalized:
            return "when_would_you_use_x_instead_of_y"
        return "how_are_x_and_y_related"

    if normalized.startswith("what is "):
        return "what_is"
    if normalized.startswith("why is "):
        return "why_is"
    if normalized.startswith("when would you use ") or normalized.startswith("when should you use "):
        return "when_to_use"
    if normalized.startswith("how does ") or normalized.startswith("how do "):
        return "how_does_it_work"
    if normalized.startswith("what is ") and " used for" in normalized:
        return "what_is_it_used_for"
    return "what_is"


def _normalize_relationship_type(value: object) -> str:
    normalized = re.sub(r"[\s\-]+", "_", str(value or "").strip().lower())
    if normalized in {
        "paired_scope",
        "prerequisite_adjacent",
        "commonly_confused",
        "comparison_worthy",
        "used_together",
        "evaluation_related",
    }:
        return normalized
    if normalized in {"procedure_on_concept", "foundation", "foundational_skills"}:
        return "prerequisite_adjacent"
    if normalized in {"related_data_structures"}:
        return "paired_scope"
    if normalized in {"comparison", "compare", "contrast"}:
        return "comparison_worthy"
    if normalized in {"related", "relationship", "connected"}:
        return "used_together"
    return "used_together"
