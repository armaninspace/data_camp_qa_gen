from __future__ import annotations

from collections import defaultdict
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
from course_pipeline.pricing import load_pricing_snapshot
from course_pipeline.run_logging import RunLogger
from course_pipeline.schemas import (
    AnswerRecord,
    CanonicalTopic,
    CacheRow,
    CourseBundle,
    CourseContextFrame,
    GeneratedQuestion,
    LedgerRow,
    NormalizedCourse,
    QuestionContextFrame,
    RelatedTopicPair,
    QuestionValidationRecord,
    SemanticReviewDecision,
    SemanticStageResult,
    TrainRow,
    Topic,
    TeacherAnswerDraft,
    ExcludedCourseRecord,
    VettedTopic,
    VettedTopicPair,
)


RUN_ARTIFACT_NAMES = [
    "excluded_courses.jsonl",
    "normalized_courses.jsonl",
    "course_context_frames.jsonl",
    "question_context_frames.jsonl",
    "train_rows.jsonl",
    "cache_rows.jsonl",
    "semantic_topics.jsonl",
    "semantic_correlated_topics.jsonl",
    "semantic_topic_questions.jsonl",
    "semantic_correlated_topic_questions.jsonl",
    "semantic_synthetic_answers.jsonl",
    "semantic_review_decisions.jsonl",
    "answers.jsonl",
    "all_rows.jsonl",
]
PUBLISHED_ARTIFACT_NAMES = [
    "normalized_courses.jsonl",
    "course_context_frames.jsonl",
    "question_context_frames.jsonl",
    "train_rows.jsonl",
    "cache_rows.jsonl",
    "semantic_topics.jsonl",
    "semantic_correlated_topics.jsonl",
    "semantic_topic_questions.jsonl",
    "semantic_correlated_topic_questions.jsonl",
    "semantic_synthetic_answers.jsonl",
    "semantic_review_decisions.jsonl",
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
    answers: list[AnswerRecord],
    rows: list[LedgerRow],
    related_pairs: list[RelatedTopicPair] | None = None,
    vetted_topics: list[VettedTopic] | None = None,
    vetted_pairs: list[VettedTopicPair] | None = None,
    single_topic_questions: list[GeneratedQuestion] | None = None,
    pairwise_questions: list[GeneratedQuestion] | None = None,
    validations: list[QuestionValidationRecord] | None = None,
    synthetic_answers: list | None = None,
    synthetic_validations: list | None = None,
    synthetic_rewrites: list[dict] | None = None,
    semantic_result: SemanticStageResult | None = None,
    semantic_review_decisions: list[SemanticReviewDecision] | None = None,
    course_context_frame: CourseContextFrame | None = None,
    question_context_frames: list[QuestionContextFrame] | None = None,
    teacher_answer_drafts: list[TeacherAnswerDraft] | None = None,
    train_rows: list[TrainRow] | None = None,
    cache_rows: list[CacheRow] | None = None,
) -> None:
    out = Path(output_dir)
    course_ids = {course.course_id}
    related_pairs = related_pairs or []
    single_topic_questions = single_topic_questions or []
    pairwise_questions = pairwise_questions or []
    validations = validations or []
    semantic_review_decisions = semantic_review_decisions or []
    question_context_frames = question_context_frames or []
    teacher_answer_drafts = teacher_answer_drafts or []
    train_rows = train_rows or []
    cache_rows = cache_rows or []

    upsert_jsonl_rows(out / "normalized_courses.jsonl", [course], course_ids)
    upsert_jsonl_rows(
        out / "course_context_frames.jsonl",
        [] if course_context_frame is None else [course_context_frame],
        course_ids,
    )
    upsert_jsonl_rows(
        out / "question_context_frames.jsonl",
        question_context_frames,
        course_ids,
    )
    upsert_jsonl_rows(
        out / "train_rows.jsonl",
        train_rows,
        course_ids,
    )
    upsert_jsonl_rows(
        out / "cache_rows.jsonl",
        cache_rows,
        course_ids,
    )
    semantic_topics = [] if semantic_result is None else [
        {"course_id": course.course_id, **item.model_dump()}
        for item in semantic_result.topics
    ]
    semantic_correlated_topics = [] if semantic_result is None else [
        {"course_id": course.course_id, **item.model_dump()}
        for item in semantic_result.correlated_topics
    ]
    semantic_topic_questions = [] if semantic_result is None else [
        {"course_id": course.course_id, **item.model_dump()}
        for item in semantic_result.topic_questions
    ]
    semantic_correlated_topic_questions = [] if semantic_result is None else [
        {"course_id": course.course_id, **item.model_dump()}
        for item in semantic_result.correlated_topic_questions
    ]
    semantic_synthetic_answers = [] if semantic_result is None else [
        {"course_id": course.course_id, **item.model_dump()}
        for item in semantic_result.synthetic_answers
    ]
    upsert_jsonl_rows(out / "semantic_topics.jsonl", semantic_topics, course_ids)
    upsert_jsonl_rows(
        out / "semantic_correlated_topics.jsonl",
        semantic_correlated_topics,
        course_ids,
    )
    upsert_jsonl_rows(
        out / "semantic_topic_questions.jsonl",
        semantic_topic_questions,
        course_ids,
    )
    upsert_jsonl_rows(
        out / "semantic_correlated_topic_questions.jsonl",
        semantic_correlated_topic_questions,
        course_ids,
    )
    upsert_jsonl_rows(
        out / "semantic_synthetic_answers.jsonl",
        semantic_synthetic_answers,
        course_ids,
    )
    upsert_jsonl_rows(
        out / "semantic_review_decisions.jsonl",
        [
            {"course_id": course.course_id, **item.model_dump()}
            for item in semantic_review_decisions
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
        semantic_stage_result=semantic_result,
        semantic_review_decisions=semantic_review_decisions,
        course_context_frame=course_context_frame,
        question_context_frames=question_context_frames,
        train_rows=train_rows,
        cache_rows=cache_rows,
        answers=answers,
        final_rows=rows,
        summary={
            "course_context_frame_count": 0 if course_context_frame is None else 1,
            "question_context_frame_count": len(question_context_frames),
            "teacher_answer_count": len(teacher_answer_drafts),
            "train_row_count": len(train_rows),
            "cache_row_count": len(cache_rows),
            "semantic_topic_count": 0 if semantic_result is None else len(semantic_result.topics),
            "semantic_correlated_topic_count": (
                0 if semantic_result is None else len(semantic_result.correlated_topics)
            ),
            "semantic_question_count": (
                0
                if semantic_result is None
                else len(semantic_result.topic_questions)
                + len(semantic_result.correlated_topic_questions)
            ),
            "semantic_answer_count": (
                0 if semantic_result is None else len(semantic_result.synthetic_answers)
            ),
            "review_decision_count": len(semantic_review_decisions),
            "answered_count": sum(row.status == "answered" for row in rows),
            "rejected_question_count": sum(row.status == "rejected" for row in rows),
            "errored_question_count": sum(row.status == "errored" for row in rows),
            "correct_count": sum(a.correctness == "correct" for a in answers),
            "incorrect_count": sum(a.correctness == "incorrect" for a in answers),
            "uncertain_count": sum(a.correctness == "uncertain" for a in answers),
        },
    )
    write_yaml(out / "course_yaml" / f"{course.course_id}.yaml", bundle)


def rebuild_run_summary(output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    bundle_rows, shared_rows_by_course, answers_by_course = _collect_consistency_state(out)
    validate_rendered_output_consistency(out)
    bundles = []
    for course_id in sorted(bundle_rows):
        bundle = bundle_rows[course_id]
        shared_rows = shared_rows_by_course.get(course_id, [])
        bundles.append(
            {
                "course_id": course_id,
                "title": bundle["title"],
                "row_count": len(shared_rows),
                "answered_count": sum(
                    row.get("status") == "answered" for row in shared_rows if isinstance(row, dict)
                ),
                "rejected_count": sum(
                    row.get("status") == "rejected" for row in shared_rows if isinstance(row, dict)
                ),
                "errored_count": sum(
                    row.get("status") == "errored" for row in shared_rows if isinstance(row, dict)
                ),
                "shared_answer_count": len(answers_by_course.get(course_id, [])),
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
        "course_context_frame_count": len(read_jsonl(out / "course_context_frames.jsonl")),
        "question_context_frame_count": len(read_jsonl(out / "question_context_frames.jsonl")),
        "train_row_count": len(read_jsonl(out / "train_rows.jsonl")),
        "cache_row_count": len(read_jsonl(out / "cache_rows.jsonl")),
        "semantic_topic_count": len(read_jsonl(out / "semantic_topics.jsonl")),
        "semantic_correlated_topic_count": len(
            read_jsonl(out / "semantic_correlated_topics.jsonl")
        ),
        "semantic_question_count": len(read_jsonl(out / "semantic_topic_questions.jsonl"))
        + len(read_jsonl(out / "semantic_correlated_topic_questions.jsonl")),
        "semantic_answer_count": len(read_jsonl(out / "semantic_synthetic_answers.jsonl")),
        "review_decision_count": len(read_jsonl(out / "semantic_review_decisions.jsonl")),
        "answered_count": sum(item["answered_count"] for item in bundles),
        "rejected_question_count": sum(item["rejected_count"] for item in bundles),
        "errored_question_count": sum(item["errored_count"] for item in bundles),
        "correct_count": sum(
            row.get("correctness") == "correct" for row in read_jsonl(out / "answers.jsonl")
        ),
        "incorrect_count": sum(
            row.get("correctness") == "incorrect" for row in read_jsonl(out / "answers.jsonl")
        ),
        "uncertain_count": sum(
            row.get("correctness") == "uncertain" for row in read_jsonl(out / "answers.jsonl")
        ),
    }
    quality_metrics = _quality_metrics(out)
    llm_metrics = _llm_usage_cost_metrics(out)
    summary.update(quality_metrics)
    summary.update(llm_metrics)
    summary["rejected_count"] = summary["rejected_question_count"]
    summary["errored_count"] = summary["errored_question_count"]
    summary["quality_metrics"] = quality_metrics
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


def validate_rendered_output_consistency(output_dir: str | Path) -> None:
    out = Path(output_dir)
    bundle_rows, shared_rows_by_course, answers_by_course = _collect_consistency_state(out)
    issues: list[str] = []

    shared_answered_count = 0
    for shared_rows in shared_rows_by_course.values():
        shared_answered_count += sum(
            row.get("status") == "answered" for row in shared_rows if isinstance(row, dict)
        )

    all_answers = read_jsonl(out / "answers.jsonl")
    non_synthetic_answers = [
        row
        for row in all_answers
        if row.get("answer_mode") not in {None, "synthetic_tutor_answer"}
    ]
    if non_synthetic_answers:
        issues.append(
            "shared answers.jsonl contains non-synthetic answer_mode rows"
        )
    if len(all_answers) != shared_answered_count:
        issues.append(
            "shared answers.jsonl row count does not match answered rows in all_rows.jsonl"
        )

    bundle_course_ids = set(bundle_rows)
    shared_course_ids = set(shared_rows_by_course)
    answer_course_ids = set(answers_by_course)

    missing_bundle_courses = sorted((shared_course_ids | answer_course_ids) - bundle_course_ids)
    if missing_bundle_courses:
        issues.append(
            "shared artifacts reference courses without course_yaml bundles: "
            + ", ".join(missing_bundle_courses)
        )

    for course_id, bundle in sorted(bundle_rows.items()):
        bundle_final_rows = bundle["final_rows"]
        bundle_answers = bundle["answers"]
        shared_rows = shared_rows_by_course.get(course_id, [])
        shared_answers = answers_by_course.get(course_id, [])
        bundle_answered_count = sum(
            row.get("status") == "answered"
            for row in bundle_final_rows
            if isinstance(row, dict)
        )
        shared_answered_for_course = sum(
            row.get("status") == "answered"
            for row in shared_rows
            if isinstance(row, dict)
        )

        if bundle_final_rows and not shared_rows:
            issues.append(
                f"course {course_id} has final_rows in course_yaml but no shared all_rows.jsonl rows"
            )
        if len(bundle_final_rows) != len(shared_rows):
            issues.append(
                f"course {course_id} final_rows count {len(bundle_final_rows)} != shared all_rows count {len(shared_rows)}"
            )
        if bundle_answered_count != shared_answered_for_course:
            issues.append(
                f"course {course_id} answered rows in course_yaml ({bundle_answered_count}) != shared answered rows ({shared_answered_for_course})"
            )
        if bundle_answered_count != len(shared_answers):
            issues.append(
                f"course {course_id} answered rows in course_yaml ({bundle_answered_count}) != shared answers.jsonl rows ({len(shared_answers)})"
            )
        if len(bundle_answers) != len(shared_answers):
            issues.append(
                f"course {course_id} bundle answers count {len(bundle_answers)} != shared answers.jsonl count {len(shared_answers)}"
            )
        if any(
            row.get("answer_mode") not in {None, "synthetic_tutor_answer"}
            for row in bundle_answers
            if isinstance(row, dict)
        ):
            issues.append(
                f"course {course_id} course_yaml answers include non-synthetic answer_mode rows"
            )

    if issues:
        raise RuntimeError(
            "rendered output consistency check failed: " + "; ".join(issues)
        )


def _row_course_id(row: dict[str, Any]) -> str | None:
    value = row.get("course_id")
    if value is not None:
        return str(value)
    course = row.get("course")
    if isinstance(course, dict) and course.get("course_id") is not None:
        return str(course["course_id"])
    return None


def _collect_consistency_state(
    output_dir: Path,
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:
    bundle_rows: dict[str, dict[str, Any]] = {}
    for bundle_path in sorted((output_dir / "course_yaml").glob("*.yaml")):
        bundle = read_yaml(bundle_path)
        if not bundle:
            continue
        course_id = str(bundle.get("course_id", bundle_path.stem))
        bundle_rows[course_id] = {
            "title": bundle.get("title"),
            "final_rows": [
                row for row in bundle.get("final_rows", []) if isinstance(row, dict)
            ],
            "answers": [
                row for row in bundle.get("answers", []) if isinstance(row, dict)
            ],
        }

    shared_rows_by_course: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(output_dir / "all_rows.jsonl"):
        course_id = _row_course_id(row)
        if course_id is not None:
            shared_rows_by_course[course_id].append(row)

    answers_by_course: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(output_dir / "answers.jsonl"):
        course_id = _row_course_id(row)
        if course_id is not None:
            answers_by_course[course_id].append(row)

    return bundle_rows, dict(shared_rows_by_course), dict(answers_by_course)


def _quality_metrics(output_dir: Path) -> dict[str, Any]:
    all_rows = read_jsonl(output_dir / "all_rows.jsonl")
    single_questions = read_jsonl(output_dir / "semantic_topic_questions.jsonl")
    pairwise_questions = read_jsonl(output_dir / "semantic_correlated_topic_questions.jsonl")
    total_rows = len(all_rows)
    rejected_count = sum(row.get("status") == "rejected" for row in all_rows)
    errored_count = sum(row.get("status") == "errored" for row in all_rows)

    return {
        "reject_rate": 0.0 if total_rows == 0 else round(rejected_count / total_rows, 4),
        "errored_rate": 0.0 if total_rows == 0 else round(errored_count / total_rows, 4),
        "comparison_question_count": len(pairwise_questions),
        "entry_question_count": sum(row.get("family") == "entry" for row in single_questions),
    }


def _llm_usage_cost_metrics(output_dir: Path) -> dict[str, Any]:
    llm_calls = read_jsonl(output_dir / "logs" / "llm_calls.jsonl")
    pricing_snapshot = load_pricing_snapshot(output_dir / "logs" / "pricing_snapshot.json")

    cost_by_stage: defaultdict[str, float] = defaultdict(float)
    cost_by_model: defaultdict[str, float] = defaultdict(float)
    tokens_in_total = 0
    cached_tokens_in_total = 0
    tokens_out_total = 0
    cost_total = 0.0
    calls_with_cost = 0
    missing_usage = 0
    unknown_pricing = 0
    pricing_unavailable = 0

    for call in llm_calls:
        tokens_in = call.get("tokens_in")
        if isinstance(tokens_in, int):
            tokens_in_total += tokens_in

        cached_tokens_in = call.get("cached_tokens_in")
        if isinstance(cached_tokens_in, int):
            cached_tokens_in_total += cached_tokens_in

        tokens_out = call.get("tokens_out")
        if isinstance(tokens_out, int):
            tokens_out_total += tokens_out

        cost_status = call.get("cost_status")
        if cost_status == "missing_usage":
            missing_usage += 1
        elif cost_status == "unknown_model":
            unknown_pricing += 1
        elif cost_status == "pricing_unavailable":
            pricing_unavailable += 1

        cost_value = call.get("cost_total_usd")
        if isinstance(cost_value, (int, float)):
            calls_with_cost += 1
            cost_total += float(cost_value)
            stage = str(call.get("stage") or "unknown")
            model = str(
                call.get("resolved_pricing_model")
                or call.get("actual_model")
                or call.get("configured_model")
                or "unknown"
            )
            cost_by_stage[stage] += float(cost_value)
            cost_by_model[model] += float(cost_value)

    if not llm_calls:
        cost_reporting_status = "no_calls"
    elif missing_usage or unknown_pricing or pricing_unavailable:
        cost_reporting_status = "partial"
    else:
        cost_reporting_status = "ok"

    return {
        "llm_call_count": len(llm_calls),
        "llm_calls_with_cost": calls_with_cost,
        "llm_calls_missing_usage": missing_usage,
        "llm_calls_unknown_pricing": unknown_pricing,
        "llm_calls_pricing_unavailable": pricing_unavailable,
        "llm_tokens_in_total": tokens_in_total,
        "llm_cached_tokens_in_total": cached_tokens_in_total,
        "llm_tokens_out_total": tokens_out_total,
        "llm_cost_total_usd": _round_cost(cost_total),
        "llm_cost_by_stage": {
            key: _round_cost(value) for key, value in sorted(cost_by_stage.items())
        },
        "llm_cost_by_model": {
            key: _round_cost(value) for key, value in sorted(cost_by_model.items())
        },
        "llm_pricing_source": None if pricing_snapshot is None else pricing_snapshot.get("source_url"),
        "llm_pricing_fetched_at": None if pricing_snapshot is None else pricing_snapshot.get("fetched_at"),
        "llm_cost_reporting_status": cost_reporting_status,
    }


def _round_cost(value: float) -> float:
    return round(value, 12)
