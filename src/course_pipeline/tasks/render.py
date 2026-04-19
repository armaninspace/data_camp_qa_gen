from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

from course_pipeline.io_utils import (
    read_jsonl,
    read_yaml,
    upsert_jsonl_rows,
    write_jsonl,
    write_yaml,
)
from course_pipeline.run_logging import RunLogger
from course_pipeline.tasks.extract_topics import is_heading_like_topic
from course_pipeline.schemas import (
    AnswerRecord,
    CanonicalTopic,
    CourseBundle,
    LedgerRow,
    NormalizedCourse,
    QuestionCandidate,
    QuestionRepair,
    Topic,
    ExcludedCourseRecord,
)


RUN_ARTIFACT_NAMES = [
    "excluded_courses.jsonl",
    "normalized_courses.jsonl",
    "topics.jsonl",
    "canonical_topics.jsonl",
    "question_candidates.jsonl",
    "question_repairs.jsonl",
    "answers.jsonl",
    "all_rows.jsonl",
]
PUBLISHED_ARTIFACT_NAMES = [
    "normalized_courses.jsonl",
    "topics.jsonl",
    "canonical_topics.jsonl",
    "question_candidates.jsonl",
    "question_repairs.jsonl",
    "answers.jsonl",
    "all_rows.jsonl",
]


def write_excluded_courses(
    output_dir: str | Path,
    excluded_courses: list[ExcludedCourseRecord],
) -> None:
    out = Path(output_dir)
    write_jsonl(
        out / "excluded_courses.jsonl",
        [item.model_dump() for item in excluded_courses],
    )


def persist_stage_artifacts(
    output_dir: str | Path,
    course: NormalizedCourse,
    topics: list[Topic],
    canonical_topics: list[CanonicalTopic],
    candidates: list[QuestionCandidate],
    repairs: list[QuestionRepair],
    answers: list[AnswerRecord],
    rows: list[LedgerRow],
) -> None:
    out = Path(output_dir)
    course_ids = {course.course_id}

    upsert_jsonl_rows(out / "normalized_courses.jsonl", [course], course_ids)
    upsert_jsonl_rows(
        out / "topics.jsonl",
        [{"course_id": course.course_id, **topic.model_dump()} for topic in topics],
        course_ids,
    )
    upsert_jsonl_rows(
        out / "canonical_topics.jsonl",
        [
            {"course_id": course.course_id, **topic.model_dump()}
            for topic in canonical_topics
        ],
        course_ids,
    )
    upsert_jsonl_rows(
        out / "question_candidates.jsonl",
        [
            {"course_id": course.course_id, **candidate.model_dump()}
            for candidate in candidates
        ],
        course_ids,
    )
    upsert_jsonl_rows(
        out / "question_repairs.jsonl",
        [
            {"course_id": course.course_id, **repair.model_dump()}
            for repair in repairs
        ],
        course_ids,
    )
    upsert_jsonl_rows(
        out / "answers.jsonl",
        [
            {"course_id": course.course_id, **answer.model_dump()}
            for answer in answers
        ],
        course_ids,
    )
    upsert_jsonl_rows(out / "all_rows.jsonl", rows, course_ids)

    bundle = CourseBundle(
        course_id=course.course_id,
        title=course.title,
        normalized_course=course,
        extracted_topics=topics,
        canonical_topics=canonical_topics,
        question_candidates=candidates,
        question_repairs=repairs,
        answers=answers,
        final_rows=rows,
        summary={
            "topic_count": len(topics),
            "canonical_topic_count": len(canonical_topics),
            "candidate_count": len(candidates),
            "accepted_count": sum(r.status != "rejected" for r in repairs),
            "rejected_count": sum(r.status == "rejected" for r in repairs),
            "correct_count": sum(a.correctness == "correct" for a in answers),
            "uncertain_count": sum(a.correctness == "uncertain" for a in answers),
        },
    )
    write_yaml(out / "course_yaml" / f"{course.course_id}.yaml", bundle)


def rebuild_run_summary(output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    bundles: list[dict[str, Any]] = []
    for bundle_path in sorted((out / "course_yaml").glob("*.yaml")):
        bundle = read_yaml(bundle_path)
        if not bundle:
            continue
        rows = bundle.get("final_rows", [])
        bundles.append(
            {
                "course_id": str(bundle.get("course_id", bundle_path.stem)),
                "title": bundle.get("title"),
                "row_count": len(rows),
                "answered_count": sum(
                    row.get("status") == "answered" for row in rows if isinstance(row, dict)
                ),
                "rejected_count": sum(
                    row.get("status") == "rejected" for row in rows if isinstance(row, dict)
                ),
                "errored_count": sum(
                    row.get("status") == "errored" for row in rows if isinstance(row, dict)
                ),
            }
        )

    summary = {
        "course_count": len(bundles),
        "excluded_course_count": len(read_jsonl(out / "excluded_courses.jsonl")),
        "courses": bundles,
        "artifact_counts": {
            artifact_name: len(read_jsonl(out / artifact_name))
            for artifact_name in RUN_ARTIFACT_NAMES
        },
        "answered_count": sum(item["answered_count"] for item in bundles),
        "rejected_count": sum(item["rejected_count"] for item in bundles),
        "errored_count": sum(item["errored_count"] for item in bundles),
        "quality_metrics": _quality_metrics(out),
    }
    write_yaml(out / "run_summary.yaml", summary)
    return summary


def publish_final_outputs(
    *,
    run_dir: str | Path,
    final_dir: str | Path,
    affected_course_ids: set[str],
    logger: RunLogger,
) -> dict[str, Any]:
    run_root = Path(run_dir)
    final_root = Path(final_dir)
    final_root.mkdir(parents=True, exist_ok=True)

    missing_bundles = [
        course_id
        for course_id in sorted(affected_course_ids)
        if not (run_root / "course_yaml" / f"{course_id}.yaml").exists()
    ]
    if missing_bundles:
        logger.log_publish(
            f"publish blocked missing_course_bundles={missing_bundles}",
            level="ERROR",
        )
        raise RuntimeError(
            f"publish blocked; missing course bundles for {', '.join(missing_bundles)}"
        )

    missing_artifacts = [
        artifact_name
        for artifact_name in PUBLISHED_ARTIFACT_NAMES
        if not (run_root / artifact_name).exists()
    ]
    if missing_artifacts:
        logger.log_publish(
            f"publish blocked missing_shared_artifacts={missing_artifacts}",
            level="ERROR",
        )
        raise RuntimeError(
            f"publish blocked; missing shared artifacts: {', '.join(missing_artifacts)}"
        )

    for artifact_name in PUBLISHED_ARTIFACT_NAMES:
        rows = [
            row
            for row in read_jsonl(run_root / artifact_name)
            if _row_course_id(row) in affected_course_ids
        ]
        upsert_jsonl_rows(final_root / artifact_name, rows, affected_course_ids)
        logger.log_publish(
            f"upserted {artifact_name} affected_courses={len(affected_course_ids)} rows={len(rows)}"
        )

    for course_id in sorted(affected_course_ids):
        source_bundle = run_root / "course_yaml" / f"{course_id}.yaml"
        target_bundle = final_root / "course_yaml" / f"{course_id}.yaml"
        target_bundle.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_bundle, target_bundle)
        logger.log_publish(f"published course bundle course_id={course_id}")

    summary = rebuild_run_summary(final_root)
    logger.log_publish(
        f"publish complete course_count={summary['course_count']} answered_count={summary['answered_count']}"
    )
    return summary


def _row_course_id(row: dict[str, Any]) -> str | None:
    value = row.get("course_id")
    if value is not None:
        return str(value)
    course = row.get("course")
    if isinstance(course, dict) and course.get("course_id") is not None:
        return str(course["course_id"])
    return None


def _quality_metrics(output_dir: Path) -> dict[str, Any]:
    canonical_topics = read_jsonl(output_dir / "canonical_topics.jsonl")
    all_rows = read_jsonl(output_dir / "all_rows.jsonl")
    candidates = read_jsonl(output_dir / "question_candidates.jsonl")

    heading_like_count = sum(
        is_heading_like_topic(row.get("label", ""))
        for row in canonical_topics
        if isinstance(row, dict)
    )
    total_topics = len(canonical_topics)
    total_rows = len(all_rows)
    rejected_count = sum(row.get("status") == "rejected" for row in all_rows)
    errored_count = sum(row.get("status") == "errored" for row in all_rows)
    comparison_count = sum(row.get("family") == "comparison" for row in candidates)
    entry_count = sum(row.get("family") == "entry" for row in candidates)

    return {
        "heading_like_canonical_topic_rate": 0.0
        if total_topics == 0
        else round(heading_like_count / total_topics, 4),
        "reject_rate": 0.0 if total_rows == 0 else round(rejected_count / total_rows, 4),
        "errored_rate": 0.0 if total_rows == 0 else round(errored_count / total_rows, 4),
        "comparison_question_count": comparison_count,
        "entry_question_count": entry_count,
    }
