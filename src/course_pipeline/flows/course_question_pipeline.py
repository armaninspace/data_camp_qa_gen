from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math

from prefect import flow, task

from course_pipeline.config import Settings
from course_pipeline.io_utils import normalized_relative_paths, write_jsonl
from course_pipeline.llm import LLMClient
from course_pipeline.run_logging import RunLogger, StageTimer
from course_pipeline.tasks.build_ledger import build_ledger_rows
from course_pipeline.tasks.canonicalize import canonicalize_topics
from course_pipeline.tasks.discover_related_pairs import discover_related_pairs
from course_pipeline.tasks.extract_topics import extract_atomic_topics_baseline
from course_pipeline.tasks.generate_questions import (
    generate_pairwise_questions,
    generate_single_topic_questions,
)
from course_pipeline.tasks.normalize import load_raw_course, normalize_course_record
from course_pipeline.tasks.preflight_validate import preflight_validate_course
from course_pipeline.tasks.render import (
    persist_stage_artifacts,
    publish_final_outputs,
    rebuild_run_summary,
)
from course_pipeline.tasks.repair_questions import validate_questions
from course_pipeline.tasks.synthesize_answers import (
    synthesize_answers_for_course,
    synthetic_results_to_answer_records,
)
from course_pipeline.tasks.vet_topics import vet_topics_and_pairs
from course_pipeline.schemas import (
    GeneratedQuestion,
    QuestionCandidate,
    QuestionRepair,
    QuestionValidationRecord,
)


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
    synth_client: LLMClient,
    validate_client: LLMClient,
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
        stage="extract_atomic_topics",
        input_row_count=len(course.chapters),
    )
    topics = extract_atomic_topics_baseline(course)
    timer.finish(output_row_count=len(topics))

    timer = StageTimer(
        logger,
        course_id=course.course_id,
        stage="canonicalize_topics",
        input_row_count=len(topics),
    )
    canonical_topics = canonicalize_topics(topics)
    timer.finish(output_row_count=len(canonical_topics))

    timer = StageTimer(
        logger,
        course_id=course.course_id,
        stage="discover_related_pairs",
        input_row_count=len(canonical_topics),
    )
    related_pairs = discover_related_pairs(canonical_topics)
    timer.finish(output_row_count=len(related_pairs))

    timer = StageTimer(
        logger,
        course_id=course.course_id,
        stage="vet_topics",
        input_row_count=len(canonical_topics) + len(related_pairs),
    )
    vetted_topics, vetted_pairs = vet_topics_and_pairs(canonical_topics, related_pairs)
    timer.finish(output_row_count=len(vetted_topics) + len(vetted_pairs))

    kept_vetted_topics = [item for item in vetted_topics if item.decision != "reject"]
    kept_vetted_pairs = [item for item in vetted_pairs if item.decision == "keep_pair"]

    timer = StageTimer(
        logger,
        course_id=course.course_id,
        stage="generate_single_topic_questions",
        input_row_count=len(vetted_topics),
    )
    single_topic_questions = generate_single_topic_questions(kept_vetted_topics)
    timer.finish(output_row_count=len(single_topic_questions))

    timer = StageTimer(
        logger,
        course_id=course.course_id,
        stage="generate_pairwise_questions",
        input_row_count=len(vetted_pairs),
    )
    pairwise_questions = (
        generate_pairwise_questions(kept_vetted_pairs) if kept_vetted_topics else []
    )
    timer.finish(output_row_count=len(pairwise_questions))

    all_generated_questions = [*single_topic_questions, *pairwise_questions]
    timer = StageTimer(
        logger,
        course_id=course.course_id,
        stage="validate_questions",
        input_row_count=len(all_generated_questions),
    )
    validations = validate_questions(all_generated_questions)
    timer.finish(output_row_count=len(validations))

    candidates = _legacy_candidates(all_generated_questions)
    repairs = _legacy_repairs(validations)

    timer = StageTimer(
        logger,
        course_id=course.course_id,
        stage="synthesize_answers",
        input_row_count=len(validations),
    )
    synth_result = synthesize_answers_for_course(
        run_id=Path(output_dir).name,
        course=course.model_dump(),
        canonical_topics=[
            {"course_id": course.course_id, **topic.model_dump()} for topic in canonical_topics
        ],
        validations=[{"course_id": course.course_id, **item.model_dump()} for item in validations],
        related_pairs=[
            {"course_id": course.course_id, **pair.model_dump()} for pair in related_pairs
        ],
        synth_client=synth_client,
        validate_client=validate_client,
        logger=logger,
    )
    answers = synthetic_results_to_answer_records(
        synthetic_answers=synth_result.synthetic_answers,
        validations=synth_result.validations,
        question_provenance={
            item.question_id: {
                "topic_labels": item.relevant_topics,
                "source_refs": [span.source for span in item.evidence_spans],
                "evidence_spans": [span.model_dump() for span in item.evidence_spans],
            }
            for item in validations
        },
    )
    timer.finish(output_row_count=len(answers))

    timer = StageTimer(
        logger,
        course_id=course.course_id,
        stage="build_ledger_rows",
        input_row_count=len(repairs),
    )
    rows = build_ledger_rows(course, candidates, repairs, answers)
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
        candidates=candidates,
        repairs=repairs,
        answers=answers,
        rows=rows,
        related_pairs=related_pairs,
        vetted_topics=vetted_topics,
        vetted_pairs=vetted_pairs,
        single_topic_questions=single_topic_questions,
        pairwise_questions=pairwise_questions,
        validations=validations,
        synthetic_answers=synth_result.synthetic_answers,
        synthetic_validations=synth_result.validations,
        synthetic_rewrites=synth_result.rewrites,
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


def _legacy_candidates(questions: list[GeneratedQuestion]) -> list[QuestionCandidate]:
    return [
        QuestionCandidate(
            candidate_id=question.question_id,
            relevant_topics=question.relevant_topics,
            family=question.family,
            pattern=question.pattern,
            question_text=question.question_text,
        )
        for question in questions
    ]


def _legacy_repairs(validations: list[QuestionValidationRecord]) -> list[QuestionRepair]:
    return [
        QuestionRepair(
            candidate_id=validation.question_id,
            status=validation.status,
            original_text=validation.original_text,
            final_text=validation.final_text,
            reject_reason=validation.reject_reason,
        )
        for validation in validations
    ]


@flow(name="course-question-pipeline-flow")
def course_question_pipeline_flow(
    input_dir: str,
    output_dir: str,
    final_dir: str = "data/final",
    slice_start: float = 0.0,
    slice_end: float = 100.0,
    publish: bool = True,
    synth_client: LLMClient | None = None,
    validate_client: LLMClient | None = None,
) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    logger = RunLogger(run_id=output.name or "run", root_dir=output)
    logger.ensure_files()
    settings = Settings()
    synth_client = synth_client or LLMClient(
        api_key=settings.openai_api_key,
        model=settings.model_synth_answer,
    )
    validate_client = validate_client or LLMClient(
        api_key=settings.openai_api_key,
        model=settings.model_synth_validate,
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
                synth_client,
                validate_client,
                quality_status=selected.quality_status,
            )
        )

    run_summary = rebuild_run_summary(output)
    logger.log_pipeline(
        f"run summary rebuilt course_count={run_summary['course_count']} excluded_course_count={run_summary['excluded_course_count']}"
    )

    if len(preflight.excluded_rows) == 0 and run_summary["rejected_question_count"] == 0:
        raise RuntimeError(
            "rejection pressure gate failed: no excluded courses and no rejected questions"
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


if __name__ == "__main__":
    course_question_pipeline_flow(
        input_dir="data/scraped",
        output_dir="data/pipeline_runs/dev_run",
    )
