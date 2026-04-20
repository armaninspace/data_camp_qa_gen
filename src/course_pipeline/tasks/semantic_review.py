from __future__ import annotations

from pathlib import Path
import json
import time

import yaml

from course_pipeline.llm import LLMClient
from course_pipeline.run_logging import RunLogger
from course_pipeline.schemas import NormalizedCourse, SemanticReviewResult, SemanticStageResult


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "semantic_review.md"


def run_semantic_review_for_course(
    *,
    course: NormalizedCourse | dict,
    semantic_result: SemanticStageResult | dict,
    llm_client: LLMClient,
    logger: RunLogger | None = None,
) -> SemanticReviewResult:
    course_payload = (
        course.model_dump(mode="json") if hasattr(course, "model_dump") else dict(course)
    )
    semantic_payload = (
        semantic_result.model_dump(mode="json")
        if hasattr(semantic_result, "model_dump")
        else dict(semantic_result)
    )
    prompt = _render_review_prompt(course_payload, semantic_payload)

    started = time.perf_counter()
    review_json = llm_client.complete_json(prompt, "semantic_review")
    latency_ms = int((time.perf_counter() - started) * 1000)

    course_id = str(course_payload["course_id"])
    if logger is not None:
        logger.log_llm_call(
            course_id=course_id,
            stage="semantic_review",
            prompt_family="semantic_review",
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

    return SemanticReviewResult.model_validate(review_json)


def _render_review_prompt(course_payload: dict, semantic_payload: dict) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    course_yaml = yaml.safe_dump(
        course_payload,
        sort_keys=False,
        allow_unicode=True,
        width=80,
    ).strip()
    semantic_json = json.dumps(semantic_payload, ensure_ascii=False, indent=2)
    return (
        template.replace("{{NORMALIZED_COURSE_YAML}}", course_yaml)
        .replace("{{SEMANTIC_BUNDLE_JSON}}", semantic_json)
    )
