from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math

from prefect import flow, task

from course_pipeline.io_utils import normalized_relative_paths
from course_pipeline.run_logging import RunLogger, StageTimer
from course_pipeline.tasks.answer_questions import answer_questions
from course_pipeline.tasks.build_ledger import build_ledger_rows
from course_pipeline.tasks.canonicalize import canonicalize_topics
from course_pipeline.tasks.extract_topics import extract_atomic_topics_baseline
from course_pipeline.tasks.generate_questions import generate_question_candidates
from course_pipeline.tasks.normalize import load_raw_course, normalize_course_record
from course_pipeline.tasks.render import (
    persist_stage_artifacts,
    publish_final_outputs,
    rebuild_run_summary,
)
from course_pipeline.tasks.repair_questions import repair_or_reject_questions


@dataclass
class SelectedCoursePath:
    relative_path: str
    absolute_path: str


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


def _process_course(path: str, output_dir: str, logger: RunLogger) -> dict:
    raw = load_raw_course(path)
    course = normalize_course_record(raw)
    logger.log_pipeline(f"processing course_id={course.course_id} path={path}")

    timer = StageTimer(logger, course_id=course.course_id, stage="normalize_course", input_row_count=1)
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
        stage="generate_question_candidates",
        input_row_count=len(canonical_topics),
    )
    candidates = generate_question_candidates(canonical_topics)
    timer.finish(output_row_count=len(candidates))

    timer = StageTimer(
        logger,
        course_id=course.course_id,
        stage="repair_or_reject_questions",
        input_row_count=len(candidates),
    )
    repairs = repair_or_reject_questions(candidates)
    timer.finish(output_row_count=len(repairs))

    timer = StageTimer(
        logger,
        course_id=course.course_id,
        stage="answer_questions",
        input_row_count=len(repairs),
    )
    answers = answer_questions(course, canonical_topics, repairs)
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
) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    logger = RunLogger(run_id=output.name or "run", root_dir=output)
    logger.ensure_files()
    logger.log_pipeline(
        f"run start input_dir={input_dir} output_dir={output_dir} slice={slice_start}-{slice_end}"
    )

    paths = load_course_paths(input_dir=input_dir, slice_start=slice_start, slice_end=slice_end)
    logger.log_pipeline(f"selected_courses={len(paths)}")

    summaries = []
    for selected in paths:
        summaries.append(_process_course(selected.absolute_path, output_dir, logger))

    run_summary = rebuild_run_summary(output)
    logger.log_pipeline(
        f"run summary rebuilt course_count={run_summary['course_count']} answered_count={run_summary['answered_count']}"
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
        "selected_course_count": len(paths),
        "courses": summaries,
    }


if __name__ == "__main__":
    course_question_pipeline_flow(
        input_dir="data/scraped",
        output_dir="data/pipeline_runs/dev_run",
    )
