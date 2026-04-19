
from __future__ import annotations

from pathlib import Path
from prefect import flow, task

from course_pipeline.tasks.normalize import load_raw_course, normalize_course_record
from course_pipeline.tasks.extract_topics import extract_atomic_topics_baseline
from course_pipeline.tasks.canonicalize import canonicalize_topics
from course_pipeline.tasks.generate_questions import generate_question_candidates
from course_pipeline.tasks.repair_questions import repair_or_reject_questions
from course_pipeline.tasks.answer_questions import answer_questions
from course_pipeline.tasks.build_ledger import build_ledger_rows
from course_pipeline.tasks.render import persist_stage_artifacts
from course_pipeline.io_utils import write_yaml


@task
def load_course_paths(input_dir: str) -> list[str]:
    p = Path(input_dir)
    files = sorted(
        [
            str(fp)
            for fp in p.glob("**/*")
            if fp.is_file() and fp.suffix.lower() in {".yaml", ".yml", ".json", ".md"}
        ]
    )
    return files


@task
def process_course(path: str, output_dir: str) -> dict:
    raw = load_raw_course(path)
    course = normalize_course_record(raw)
    topics = extract_atomic_topics_baseline(course)
    canonical_topics = canonicalize_topics(topics)
    candidates = generate_question_candidates(canonical_topics)
    repairs = repair_or_reject_questions(candidates)
    answers = answer_questions(course, canonical_topics, repairs)
    rows = build_ledger_rows(course, candidates, repairs, answers)
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
    return {
        "course_id": course.course_id,
        "title": course.title,
        "row_count": len(rows),
        "answered_count": sum(r.status == "answered" for r in rows),
        "rejected_count": sum(r.status == "rejected" for r in rows),
    }


@flow(name="course-question-pipeline-flow")
def course_question_pipeline_flow(input_dir: str, output_dir: str) -> list[dict]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    paths = load_course_paths(input_dir)
    summaries = []
    for path in paths:
        summaries.append(process_course(path, output_dir))

    write_yaml(
        output / "run_summary.yaml",
        {
            "course_count": len(summaries),
            "courses": summaries,
        },
    )
    return summaries


if __name__ == "__main__":
    course_question_pipeline_flow(
        input_dir="data/scraped",
        output_dir="data/pipeline_runs/dev_run",
    )
