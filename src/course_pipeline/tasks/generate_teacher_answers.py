from __future__ import annotations

from pathlib import Path
import json
import time

from course_pipeline.llm import LLMClient
from course_pipeline.run_logging import RunLogger
from course_pipeline.schemas import (
    CourseContextFrame,
    ProvidedContext,
    QuestionContextFrame,
    TeacherAnswerDraft,
)


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "generate_teacher_answer.md"


def generate_teacher_answer(
    *,
    course_context_frame: CourseContextFrame,
    question_context_frame: QuestionContextFrame,
    llm_client: LLMClient,
    logger: RunLogger | None = None,
) -> TeacherAnswerDraft:
    provided_context = ProvidedContext(
        course_context_frame=course_context_frame,
        question_context_frame=question_context_frame,
    )
    prompt = _render_teacher_answer_prompt(provided_context)

    started = time.perf_counter()
    answer_response = llm_client.complete_json_result(prompt, "teacher_answer")
    latency_ms = int((time.perf_counter() - started) * 1000)

    if logger is not None:
        logger.log_llm_call(
            course_id=course_context_frame.course_id,
            stage="generate_teacher_answer",
            prompt_family="teacher_answer",
            configured_model=llm_client.model,
            requested_model=llm_client.model,
            actual_model=answer_response.actual_model or llm_client.model,
            actual_model_source=(
                "response.model" if answer_response.actual_model else "configured_model"
            ),
            provider_request_id=answer_response.response_id,
            latency_ms=latency_ms,
            tokens_in=answer_response.usage.tokens_in,
            tokens_out=answer_response.usage.tokens_out,
            retry_count=0,
            status="success",
        )

    return TeacherAnswerDraft.model_validate(
        {
            "course_id": course_context_frame.course_id,
            "question_id": question_context_frame.question_id,
            "question_text": question_context_frame.question_text,
            "provided_context": provided_context.model_dump(mode="json"),
            "teacher_answer": answer_response.payload["teacher_answer"],
            "course_aligned": answer_response.payload.get("course_aligned", True),
            "weak_grounding": answer_response.payload.get("weak_grounding", False),
            "off_topic": answer_response.payload.get("off_topic", False),
            "needs_review": answer_response.payload.get("needs_review", False),
            "model_name": llm_client.model,
            "prompt_family": "teacher_answer",
        }
    )


def generate_teacher_answers(
    *,
    course_context_frame: CourseContextFrame,
    question_context_frames: list[QuestionContextFrame],
    llm_client: LLMClient,
    logger: RunLogger | None = None,
) -> list[TeacherAnswerDraft]:
    return [
        generate_teacher_answer(
            course_context_frame=course_context_frame,
            question_context_frame=question_context_frame,
            llm_client=llm_client,
            logger=logger,
        )
        for question_context_frame in question_context_frames
    ]


def _render_teacher_answer_prompt(provided_context: ProvidedContext) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    provided_context_json = json.dumps(
        provided_context.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    )
    return template.replace("{{PROVIDED_CONTEXT_JSON}}", provided_context_json)
