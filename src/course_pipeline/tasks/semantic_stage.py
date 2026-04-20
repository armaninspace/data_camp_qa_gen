from __future__ import annotations

from pathlib import Path
import time

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

    return SemanticStageResult.model_validate(semantic_json)


def _render_semantic_prompt(course_payload: dict) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    course_yaml = yaml.safe_dump(
        course_payload,
        sort_keys=False,
        allow_unicode=True,
        width=80,
    ).strip()
    return template.replace("{{NORMALIZED_COURSE_YAML}}", course_yaml)
