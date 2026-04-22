from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math

from prefect import flow, task

from course_pipeline.config import Settings
from course_pipeline.io_utils import normalized_relative_paths, write_jsonl
from course_pipeline.llm import LLMClient
from course_pipeline.pricing import fetch_live_pricing_snapshot
from course_pipeline.run_logging import RunLogger, StageTimer
from course_pipeline.tasks.aggregate_semantic_outputs import (
    apply_semantic_review,
    generated_questions_to_validations,
    semantic_answers_to_records,
    semantic_correlations_to_related_pairs,
    semantic_questions_to_generated_questions,
    semantic_topics_to_canonical_topics,
    semantic_topics_to_topics,
)
from course_pipeline.tasks.build_course_context import build_course_context_frame
from course_pipeline.tasks.build_product_rows import build_cache_rows, build_train_rows
from course_pipeline.tasks.build_question_context import build_question_context_frames
from course_pipeline.tasks.build_ledger import build_ledger_rows
from course_pipeline.tasks.generate_teacher_answers import generate_teacher_answers
from course_pipeline.tasks.normalize import load_raw_course, normalize_course_record
from course_pipeline.tasks.post_semantic_policy import (
    apply_post_semantic_policy,
    enforce_required_entry_coverage,
)
from course_pipeline.tasks.preflight_validate import preflight_validate_course
from course_pipeline.tasks.render import (
    persist_stage_artifacts,
    publish_final_outputs,
    rebuild_run_summary,
)
from course_pipeline.tasks.semantic_review import run_semantic_review_for_course
from course_pipeline.tasks.semantic_stage import run_semantic_stage_for_course



@dataclass
class SelectedCoursePath:
    relative_path: str
    absolute_path: str
    quality_status: str | None = None


@dataclass
class PreflightSelection:
    runnable_paths: list[SelectedCoursePath]
    excluded_rows: list[dict]
    quality_counts: dict[str, int]


def _slice_indexes(total: int, slice_start: float, slice_end: float) -> tuple[int, int]:
    start = max(0.0, min(slice_start, 100.0))
    end = max(start, min(slice_end, 100.0))
    start_idx = math.floor(total * (start / 100.0))
    end_idx = math.ceil(total * (end / 100.0))
    return start_idx, end_idx


@task
def load_course_paths(
    input_dir: str,
    slice_start: float = 0.0,
    slice_end: float = 100.0,
) -> list[SelectedCoursePath]:
    normalized = normalized_relative_paths(input_dir)
    start_idx, end_idx = _slice_indexes(len(normalized), slice_start, slice_end)
    selected = normalized[start_idx:end_idx]
    return [
        SelectedCoursePath(relative_path=relative_path, absolute_path=str(path))
        for relative_path, path in selected
    ]


@task
def preflight_validate_selected_paths(
    selected_paths: list[SelectedCoursePath],
) -> PreflightSelection:
    runnable: list[SelectedCoursePath] = []
    excluded_rows: list[dict] = []
    quality_counts = {"usable": 0, "partial": 0, "broken": 0}
    for selected in selected_paths:
        raw = load_raw_course(selected.absolute_path)
        decision = preflight_validate_course(raw, selected.relative_path)
        quality_counts[decision.quality_status] += 1
        if decision.quality_status == "broken":
            excluded_rows.append(decision.model_dump())
        else:
            runnable.append(
                SelectedCoursePath(
                    relative_path=selected.relative_path,
                    absolute_path=selected.absolute_path,
                    quality_status=decision.quality_status,
                )
            )
    return PreflightSelection(
        runnable_paths=runnable,
        excluded_rows=excluded_rows,
        quality_counts=quality_counts,
    )


def _process_course(
    path: str,
    output_dir: str,
    logger: RunLogger,
    semantic_client: LLMClient,
    review_client: LLMClient | None,
    teacher_client: LLMClient | None = None,
    *,
    quality_status: str | None,
) -> dict:
    raw = load_raw_course(path)
    course = normalize_course_record(raw)
    if quality_status:
        course.metadata["quality_status"] = quality_status
    logger.log_pipeline(f"processing course_id={course.course_id} path={path}")

    timer = StageTimer(
        logger,
        course_id=course.course_id,
        stage="normalize_course",
        input_row_count=1,
    )
    timer.finish(output_row_count=1)

    timer = StageTimer(
        logger,
        course_id=course.course_id,
        stage="semantic_stage",
        input_row_count=1,
    )
    semantic_result = run_semantic_stage_for_course(
        course=course,
        llm_client=semantic_client,
        logger=logger,
    )
    timer.finish(
        output_row_count=(
            len(semantic_result.topics)
            + len(semantic_result.correlated_topics)
            + len(semantic_result.topic_questions)
            + len(semantic_result.correlated_topic_questions)
            + len(semantic_result.synthetic_answers)
        )
    )

    timer = StageTimer(
        logger,
        course_id=course.course_id,
        stage="semantic_review",
        input_row_count=(
            len(semantic_result.topics)
            + len(semantic_result.correlated_topics)
            + len(semantic_result.topic_questions)
            + len(semantic_result.correlated_topic_questions)
            + len(semantic_result.synthetic_answers)
        ),
    )
    review_result = (
        run_semantic_review_for_course(
            course=course,
            semantic_result=semantic_result,
            llm_client=review_client,
            logger=logger,
        )
        if review_client is not None
        else None
    )
    reviewed_semantic_result = apply_semantic_review(semantic_result, review_result)
    review_output_count = len(review_result.decisions) if review_result is not None else 0
    timer.finish(output_row_count=review_output_count)

    timer = StageTimer(
        logger,
        course_id=course.course_id,
        stage="aggregate_semantic_outputs",
        input_row_count=(
            len(reviewed_semantic_result.topics)
            + len(reviewed_semantic_result.correlated_topics)
            + len(reviewed_semantic_result.topic_questions)
            + len(reviewed_semantic_result.correlated_topic_questions)
            + len(reviewed_semantic_result.synthetic_answers)
        ),
    )
    topics = semantic_topics_to_topics(reviewed_semantic_result)
    canonical_topics = semantic_topics_to_canonical_topics(reviewed_semantic_result)
    related_pairs = semantic_correlations_to_related_pairs(reviewed_semantic_result)
    single_topic_questions, pairwise_questions = semantic_questions_to_generated_questions(
        reviewed_semantic_result
    )
    all_generated_questions = [*single_topic_questions, *pairwise_questions]
    all_generated_questions, coverage_report = apply_post_semantic_policy(
        course=course,
        semantic_topics=reviewed_semantic_result.topics,
        questions=all_generated_questions,
    )
    validations = generated_questions_to_validations(all_generated_questions)
    enforce_required_entry_coverage(coverage_report)
    synthetic_answers, synthetic_validations, answers = semantic_answers_to_records(
        run_id=Path(output_dir).name,
        course_id=course.course_id,
        model_name=semantic_client.model,
        semantic_result=reviewed_semantic_result,
        questions=all_generated_questions,
    )
    course_context_frame = build_course_context_frame(course, reviewed_semantic_result)
    question_context_frames = build_question_context_frames(
        course=course,
        questions=[*reviewed_semantic_result.topic_questions, *reviewed_semantic_result.correlated_topic_questions],
        course_context_frame=course_context_frame,
    )
    teacher_answer_drafts = (
        generate_teacher_answers(
            course_context_frame=course_context_frame,
            question_context_frames=question_context_frames,
            llm_client=teacher_client,
            logger=logger,
        )
        if teacher_client is not None
        else _teacher_drafts_from_semantic_answers(
            course_context_frame=course_context_frame,
            question_context_frames=question_context_frames,
            semantic_result=reviewed_semantic_result,
            model_name=semantic_client.model,
        )
    )
    answers = _merge_answers_with_teacher_drafts(
        answers=answers,
        teacher_answer_drafts=teacher_answer_drafts,
    )
    train_rows = build_train_rows(teacher_answer_drafts)
    cache_rows = build_cache_rows(train_rows)
    timer.finish(
        output_row_count=(
            len(canonical_topics)
            + len(related_pairs)
            + len(all_generated_questions)
            + len(synthetic_answers)
            + len(train_rows)
            + len(cache_rows)
        )
    )

    timer = StageTimer(
        logger,
        course_id=course.course_id,
        stage="build_ledger_rows",
        input_row_count=len(validations),
    )
    rows = build_ledger_rows(
        course,
        all_generated_questions,
        validations,
        answers,
        teacher_answer_drafts,
    )
    timer.finish(output_row_count=len(rows))

    timer = StageTimer(
        logger,
        course_id=course.course_id,
        stage="render_per_course_yaml_bundle",
        input_row_count=len(rows),
    )
    persist_stage_artifacts(
        output_dir=output_dir,
        course=course,
        topics=topics,
        canonical_topics=canonical_topics,
        answers=answers,
        rows=rows,
        related_pairs=related_pairs,
        single_topic_questions=single_topic_questions,
        pairwise_questions=pairwise_questions,
        validations=validations,
        synthetic_answers=synthetic_answers,
        synthetic_validations=synthetic_validations,
        synthetic_rewrites=[],
        semantic_result=semantic_result,
        semantic_review_decisions=[] if review_result is None else review_result.decisions,
        course_context_frame=course_context_frame,
        question_context_frames=question_context_frames,
        teacher_answer_drafts=teacher_answer_drafts,
        train_rows=train_rows,
        cache_rows=cache_rows,
    )
    timer.finish(output_row_count=len(rows))

    return {
        "course_id": course.course_id,
        "title": course.title,
        "row_count": len(rows),
        "answered_count": sum(r.status == "answered" for r in rows),
        "rejected_count": sum(r.status == "rejected" for r in rows),
        "errored_count": sum(r.status == "errored" for r in rows),
    }
@flow(name="course-question-pipeline-flow")
def course_question_pipeline_flow(
    input_dir: str,
    output_dir: str,
    final_dir: str = "data/final",
    slice_start: float = 0.0,
    slice_end: float = 100.0,
    publish: bool = True,
    semantic_client: LLMClient | None = None,
    review_client: LLMClient | None = None,
    teacher_client: LLMClient | None = None,
) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    logger = RunLogger(run_id=output.name or "run", root_dir=output)
    logger.ensure_files()
    settings = Settings()
    uses_configured_openai_client = (
        semantic_client is None or review_client is None or teacher_client is None
    )
    if settings.openai_api_key and uses_configured_openai_client:
        pricing_snapshot = fetch_live_pricing_snapshot()
        logger.write_pricing_snapshot(pricing_snapshot)
        logger.log_pipeline(
            "pricing snapshot fetched "
            f"source={pricing_snapshot['source_url']} fetched_at={pricing_snapshot['fetched_at']}"
        )
    semantic_client = semantic_client or LLMClient(
        api_key=settings.openai_api_key,
        model=settings.model_semantic_primary,
    )
    if review_client is None and settings.openai_api_key and settings.model_semantic_review:
        review_client = LLMClient(
            api_key=settings.openai_api_key,
            model=settings.model_semantic_review,
        )
    if teacher_client is None and settings.openai_api_key and settings.model_teacher_answer:
        teacher_client = LLMClient(
            api_key=settings.openai_api_key,
            model=settings.model_teacher_answer,
        )
    logger.log_pipeline(
        f"run start input_dir={input_dir} output_dir={output_dir} slice={slice_start}-{slice_end}"
    )

    paths = load_course_paths(input_dir=input_dir, slice_start=slice_start, slice_end=slice_end)
    preflight = preflight_validate_selected_paths(paths)
    write_jsonl(output / "excluded_courses.jsonl", preflight.excluded_rows)
    logger.log_pipeline(
        "selected_courses="
        f"{len(preflight.runnable_paths)} excluded_courses={len(preflight.excluded_rows)} "
        f"usable_courses={preflight.quality_counts['usable']} "
        f"partial_courses={preflight.quality_counts['partial']} "
        f"broken_courses={preflight.quality_counts['broken']}"
    )

    summaries = []
    for selected in preflight.runnable_paths:
        summaries.append(
            _process_course(
                selected.absolute_path,
                output_dir,
                logger,
                semantic_client,
                review_client,
                teacher_client,
                quality_status=selected.quality_status,
            )
        )

    run_summary = rebuild_run_summary(output)
    logger.log_pipeline(
        f"run summary rebuilt course_count={run_summary['course_count']} excluded_course_count={run_summary['excluded_course_count']}"
    )

    published_summary = None
    affected_course_ids = {item["course_id"] for item in summaries}
    if publish and affected_course_ids:
        published_summary = publish_final_outputs(
            run_dir=output,
            final_dir=final_dir,
            affected_course_ids=affected_course_ids,
            logger=logger,
        )

    logger.log_pipeline("run complete")
    return {
        "run_summary": run_summary,
        "published_summary": published_summary,
        "slice_start": slice_start,
        "slice_end": slice_end,
        "selected_course_count": len(preflight.runnable_paths),
        "excluded_course_count": len(preflight.excluded_rows),
        "courses": summaries,
    }


def _teacher_drafts_from_semantic_answers(
    *,
    course_context_frame,
    question_context_frames,
    semantic_result,
    model_name: str,
):
    from course_pipeline.schemas import TeacherAnswerDraft

    answer_by_text = {
        item.question_text: item
        for item in semantic_result.synthetic_answers
    }
    drafts: list[TeacherAnswerDraft] = []
    for question_context_frame in question_context_frames:
        semantic_answer = answer_by_text.get(question_context_frame.question_text)
        if semantic_answer is None:
            continue
        drafts.append(
            TeacherAnswerDraft(
                course_id=course_context_frame.course_id,
                question_id=question_context_frame.question_id,
                question_text=question_context_frame.question_text,
                provided_context={
                    "course_context_frame": course_context_frame,
                    "question_context_frame": question_context_frame,
                },
                teacher_answer=semantic_answer.answer_text,
                source_refs=list(question_context_frame.support_refs),
                course_aligned=True,
                weak_grounding=False,
                off_topic=False,
                needs_review=False,
                model_name=model_name,
                prompt_family="teacher_answer",
            )
        )
    return drafts


def _merge_answers_with_teacher_drafts(
    *,
    answers,
    teacher_answer_drafts,
):
    from course_pipeline.schemas import AnswerRecord

    merged_by_question_id = {answer.question_id: answer for answer in answers}
    for draft in teacher_answer_drafts:
        existing = merged_by_question_id.get(draft.question_id)
        if existing is not None:
            if not existing.source_refs and draft.source_refs:
                merged_by_question_id[draft.question_id] = existing.model_copy(
                    update={"source_refs": list(draft.source_refs)}
                )
            continue
        if not draft.teacher_answer.strip() or draft.off_topic:
            continue
        merged_by_question_id[draft.question_id] = AnswerRecord(
            question_id=draft.question_id,
            question_text=draft.question_text,
            answer_text=draft.teacher_answer,
            correctness="correct",
            confidence=1.0,
            answer_mode="synthetic_tutor_answer",
            validation_status="accept",
            provenance={
                "teacher_model_name": draft.model_name,
                "prompt_family": draft.prompt_family,
                "answer_source": "teacher_answer_draft",
            },
            source_refs=list(draft.source_refs),
        )
    return list(merged_by_question_id.values())


if __name__ == "__main__":
    course_question_pipeline_flow(
        input_dir="data/scraped",
        output_dir="data/pipeline_runs/dev_run",
    )
