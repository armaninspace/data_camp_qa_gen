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
from course_pipeline.run_logging import RunLogger
from course_pipeline.schemas import (
    AnswerRecord,
    CanonicalTopic,
    CourseBundle,
    GeneratedQuestion,
    LedgerRow,
    NormalizedCourse,
    RelatedTopicPair,
    QuestionValidationRecord,
    SemanticReviewDecision,
    SemanticStageResult,
    Topic,
    ExcludedCourseRecord,
    VettedTopic,
    VettedTopicPair,
)


RUN_ARTIFACT_NAMES = [
    "excluded_courses.jsonl",
    "normalized_courses.jsonl",
    "semantic_topics.jsonl",
    "semantic_correlated_topics.jsonl",
    "semantic_topic_questions.jsonl",
    "semantic_correlated_topic_questions.jsonl",
    "semantic_synthetic_answers.jsonl",
    "semantic_review_decisions.jsonl",
    "topics.jsonl",
    "canonical_topics.jsonl",
    "related_topic_pairs.jsonl",
    "vetted_topics.jsonl",
    "vetted_topic_pairs.jsonl",
    "single_topic_questions.jsonl",
    "pairwise_questions.jsonl",
    "question_validation.jsonl",
    "question_candidates.jsonl",
    "question_repairs.jsonl",
    "answers.jsonl",
    "synthetic_answers.jsonl",
    "synthetic_answer_validation.jsonl",
    "synthetic_answer_rewrites.jsonl",
    "all_rows.jsonl",
]
PUBLISHED_ARTIFACT_NAMES = [
    "normalized_courses.jsonl",
    "semantic_topics.jsonl",
    "semantic_correlated_topics.jsonl",
    "semantic_topic_questions.jsonl",
    "semantic_correlated_topic_questions.jsonl",
    "semantic_synthetic_answers.jsonl",
    "semantic_review_decisions.jsonl",
    "topics.jsonl",
    "canonical_topics.jsonl",
    "related_topic_pairs.jsonl",
    "vetted_topics.jsonl",
    "vetted_topic_pairs.jsonl",
    "single_topic_questions.jsonl",
    "pairwise_questions.jsonl",
    "question_validation.jsonl",
    "question_candidates.jsonl",
    "question_repairs.jsonl",
    "answers.jsonl",
    "synthetic_answers.jsonl",
    "synthetic_answer_validation.jsonl",
    "synthetic_answer_rewrites.jsonl",
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
) -> None:
    out = Path(output_dir)
    course_ids = {course.course_id}
    related_pairs = related_pairs or []
    single_topic_questions = single_topic_questions or []
    pairwise_questions = pairwise_questions or []
    vetted_topics = vetted_topics or _default_vetted_topics(canonical_topics)
    vetted_pairs = vetted_pairs or _default_vetted_pairs(related_pairs)
    validations = validations or []
    synthetic_answers = synthetic_answers or []
    synthetic_validations = synthetic_validations or []
    synthetic_rewrites = synthetic_rewrites or []
    semantic_review_decisions = semantic_review_decisions or []
    projected_candidates = _candidate_rows_from_questions(
        course.course_id,
        [*single_topic_questions, *pairwise_questions],
    )
    projected_repairs = _repair_rows_from_validations(course.course_id, validations)

    upsert_jsonl_rows(out / "normalized_courses.jsonl", [course], course_ids)
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
        out / "related_topic_pairs.jsonl",
        [
            {"course_id": course.course_id, **pair.model_dump()}
            for pair in related_pairs
        ],
        course_ids,
    )
    upsert_jsonl_rows(
        out / "vetted_topics.jsonl",
        [
            {"course_id": course.course_id, **topic.model_dump()}
            for topic in vetted_topics
        ],
        course_ids,
    )
    upsert_jsonl_rows(
        out / "vetted_topic_pairs.jsonl",
        [
            {"course_id": course.course_id, **pair.model_dump()}
            for pair in vetted_pairs
        ],
        course_ids,
    )
    upsert_jsonl_rows(
        out / "single_topic_questions.jsonl",
        [
            {"course_id": course.course_id, **question.model_dump()}
            for question in single_topic_questions
        ],
        course_ids,
    )
    upsert_jsonl_rows(
        out / "pairwise_questions.jsonl",
        [
            {"course_id": course.course_id, **question.model_dump()}
            for question in pairwise_questions
        ],
        course_ids,
    )
    upsert_jsonl_rows(
        out / "question_validation.jsonl",
        [
            {"course_id": course.course_id, **validation.model_dump()}
            for validation in validations
        ],
        course_ids,
    )
    upsert_jsonl_rows(
        out / "question_candidates.jsonl",
        projected_candidates,
        course_ids,
    )
    upsert_jsonl_rows(
        out / "question_repairs.jsonl",
        projected_repairs,
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
    upsert_jsonl_rows(
        out / "synthetic_answers.jsonl",
        [item.model_dump() for item in synthetic_answers],
        course_ids,
    )
    upsert_jsonl_rows(
        out / "synthetic_answer_validation.jsonl",
        [item.model_dump() for item in synthetic_validations],
        course_ids,
    )
    upsert_jsonl_rows(
        out / "synthetic_answer_rewrites.jsonl",
        synthetic_rewrites,
        course_ids,
    )
    upsert_jsonl_rows(out / "all_rows.jsonl", rows, course_ids)

    bundle = CourseBundle(
        course_id=course.course_id,
        title=course.title,
        normalized_course=course,
        semantic_stage_result=semantic_result,
        semantic_review_decisions=semantic_review_decisions,
        raw_topics=topics,
        canonical_topics=canonical_topics,
        vetted_topics=vetted_topics,
        related_topic_pairs=related_pairs,
        vetted_topic_pairs=vetted_pairs,
        single_topic_questions=single_topic_questions,
        pairwise_questions=pairwise_questions,
        question_validation=validations,
        answers=answers,
        synthetic_answers=synthetic_answers,
        synthetic_answer_validation=synthetic_validations,
        synthetic_answer_rewrites=synthetic_rewrites,
        final_rows=rows,
        summary={
            "raw_topic_count": len(topics),
            "canonical_topic_count": len(canonical_topics),
            "vetted_topic_count": sum(item.decision != "reject" for item in vetted_topics),
            "related_pair_count": len(related_pairs),
            "single_topic_question_count": len(single_topic_questions),
            "pairwise_question_count": len(pairwise_questions),
            "accepted_question_count": sum(item.status != "rejected" for item in validations),
            "rejected_question_count": sum(item.status == "rejected" for item in validations),
            "correct_count": sum(a.correctness == "correct" for a in answers),
            "incorrect_count": sum(a.correctness == "incorrect" for a in answers),
            "uncertain_count": sum(a.correctness == "uncertain" for a in answers),
            "synthetic_answer_count": len(synthetic_answers),
            "synthetic_rewrite_count": sum(
                item.decision == "rewrite" for item in synthetic_validations
            ),
            "synthetic_reject_count": sum(
                item.decision == "reject" for item in synthetic_validations
            ),
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
        "total_raw_topics": len(read_jsonl(out / "topics.jsonl")),
        "total_canonical_topics": len(read_jsonl(out / "canonical_topics.jsonl")),
        "total_vetted_topics": sum(
            row.get("decision") != "reject" for row in read_jsonl(out / "vetted_topics.jsonl")
        ),
        "total_related_pairs": len(read_jsonl(out / "related_topic_pairs.jsonl")),
        "total_single_topic_questions": len(read_jsonl(out / "single_topic_questions.jsonl")),
        "total_pairwise_questions": len(read_jsonl(out / "pairwise_questions.jsonl")),
        "accepted_question_count": sum(
            row.get("status") != "rejected"
            for row in read_jsonl(out / "question_validation.jsonl")
        ),
        "answered_count": sum(item["answered_count"] for item in bundles),
        "rejected_question_count": sum(item["rejected_count"] for item in bundles),
        "errored_question_count": sum(item["errored_count"] for item in bundles),
        "synthetic_answer_count": len(read_jsonl(out / "synthetic_answers.jsonl")),
        "synthetic_accepted_count": sum(
            row.get("decision") == "accept"
            for row in read_jsonl(out / "synthetic_answer_validation.jsonl")
        ),
        "synthetic_rewrite_count": sum(
            row.get("decision") == "rewrite"
            for row in read_jsonl(out / "synthetic_answer_validation.jsonl")
        ),
        "synthetic_reject_count": sum(
            row.get("decision") == "reject"
            for row in read_jsonl(out / "synthetic_answer_validation.jsonl")
        ),
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
    summary.update(quality_metrics)
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
    single_questions = read_jsonl(output_dir / "single_topic_questions.jsonl")
    pairwise_questions = read_jsonl(output_dir / "pairwise_questions.jsonl")
    total_rows = len(all_rows)
    rejected_count = sum(row.get("status") == "rejected" for row in all_rows)
    errored_count = sum(row.get("status") == "errored" for row in all_rows)

    return {
        "reject_rate": 0.0 if total_rows == 0 else round(rejected_count / total_rows, 4),
        "errored_rate": 0.0 if total_rows == 0 else round(errored_count / total_rows, 4),
        "comparison_question_count": len(pairwise_questions),
        "entry_question_count": sum(row.get("family") == "entry" for row in single_questions),
    }


def _default_vetted_topics(canonical_topics: list[CanonicalTopic]) -> list[VettedTopic]:
    return [
        VettedTopic(
            canonical_topic_id=topic.canonical_topic_id,
            canonical_label=topic.label,
            decision="keep",
            allow_single_topic_questions=True,
            allow_pairwise_questions=True,
            reason="derived_from_canonical_topic",
            final_topic_type=topic.topic_type,
            evidence_spans=topic.evidence,
        )
        for topic in canonical_topics
    ]


def _default_vetted_pairs(related_pairs: list[RelatedTopicPair]) -> list[VettedTopicPair]:
    return [
        VettedTopicPair(
            pair_id=pair.pair_id,
            topic_x=pair.topic_x,
            topic_y=pair.topic_y,
            decision="keep_pair",
            reason="derived_from_related_pair",
            relation_type=pair.relation_type,
            evidence_spans=pair.evidence_spans,
        )
        for pair in related_pairs
    ]
def _candidate_rows_from_questions(
    course_id: str,
    questions: list[GeneratedQuestion],
) -> list[dict[str, object]]:
    return [
        {
            "course_id": course_id,
            "candidate_id": question.question_id,
            "relevant_topics": question.relevant_topics,
            "family": question.family,
            "pattern": question.pattern,
            "question_text": question.question_text,
        }
        for question in questions
    ]


def _repair_rows_from_validations(
    course_id: str,
    validations: list[QuestionValidationRecord],
) -> list[dict[str, object]]:
    return [
        {
            "course_id": course_id,
            "candidate_id": validation.question_id,
            "status": validation.status,
            "original_text": validation.original_text,
            "final_text": validation.final_text,
            "reject_reason": validation.reject_reason,
        }
        for validation in validations
    ]
