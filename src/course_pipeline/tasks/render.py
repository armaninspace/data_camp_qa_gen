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
    GeneratedQuestion,
    LedgerRow,
    NormalizedCourse,
    RelatedTopicPair,
    QuestionCandidate,
    QuestionValidationRecord,
    QuestionRepair,
    Topic,
    ExcludedCourseRecord,
    VettedTopic,
    VettedTopicPair,
)


RUN_ARTIFACT_NAMES = [
    "excluded_courses.jsonl",
    "normalized_courses.jsonl",
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
    related_pairs: list[RelatedTopicPair] | None = None,
    vetted_topics: list[VettedTopic] | None = None,
    vetted_pairs: list[VettedTopicPair] | None = None,
    single_topic_questions: list[GeneratedQuestion] | None = None,
    pairwise_questions: list[GeneratedQuestion] | None = None,
    validations: list[QuestionValidationRecord] | None = None,
    synthetic_answers: list | None = None,
    synthetic_validations: list | None = None,
    synthetic_rewrites: list[dict] | None = None,
) -> None:
    out = Path(output_dir)
    course_ids = {course.course_id}
    related_pairs = related_pairs or []
    single_topic_questions = single_topic_questions or _single_topic_questions_from_candidates(
        candidates,
        canonical_topics,
    )
    pairwise_questions = pairwise_questions or _pairwise_questions_from_candidates(candidates)
    vetted_topics = vetted_topics or _default_vetted_topics(canonical_topics)
    vetted_pairs = vetted_pairs or _default_vetted_pairs(related_pairs)
    validations = validations or _validation_records_from_repairs(repairs, candidates)
    synthetic_answers = synthetic_answers or []
    synthetic_validations = synthetic_validations or []
    synthetic_rewrites = synthetic_rewrites or []

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
    single_questions = read_jsonl(output_dir / "single_topic_questions.jsonl")
    pairwise_questions = read_jsonl(output_dir / "pairwise_questions.jsonl")
    validations = read_jsonl(output_dir / "question_validation.jsonl")
    answers = read_jsonl(output_dir / "answers.jsonl")

    heading_like_count = sum(
        is_heading_like_topic(row.get("label", ""))
        for row in canonical_topics
        if isinstance(row, dict)
    )
    total_topics = len(canonical_topics)
    total_rows = len(all_rows)
    rejected_count = sum(row.get("status") == "rejected" for row in all_rows)
    errored_count = sum(row.get("status") == "errored" for row in all_rows)
    malformed_repair_count = sum(
        row.get("status") == "repaired" and row.get("reject_reason") == "malformed"
        for row in validations
    )
    answer_rows_without_evidence_count = sum(
        not row.get("evidence") for row in answers if row.get("answer_text")
    )

    return {
        "heading_like_topic_rate": 0.0
        if total_topics == 0
        else round(heading_like_count / total_topics, 4),
        "reject_rate": 0.0 if total_rows == 0 else round(rejected_count / total_rows, 4),
        "errored_rate": 0.0 if total_rows == 0 else round(errored_count / total_rows, 4),
        "comparison_question_count": len(pairwise_questions),
        "entry_question_count": sum(row.get("family") == "entry" for row in single_questions),
        "answer_rows_without_evidence_count": answer_rows_without_evidence_count,
        "malformed_repair_count": malformed_repair_count,
    }


def _default_vetted_topics(canonical_topics: list[CanonicalTopic]) -> list[VettedTopic]:
    vetted: list[VettedTopic] = []
    for topic in canonical_topics:
        is_rejected = is_heading_like_topic(topic.label)
        vetted.append(
            VettedTopic(
                canonical_topic_id=topic.canonical_topic_id,
                canonical_label=topic.label,
                decision="reject" if is_rejected else "keep",
                allow_single_topic_questions=not is_rejected,
                allow_pairwise_questions=not is_rejected,
                reason="heading_like_topic" if is_rejected else "derived_from_canonical_topic",
                final_topic_type=topic.topic_type,
                evidence_spans=topic.evidence,
            )
        )
    return vetted


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


def _single_topic_questions_from_candidates(
    candidates: list[QuestionCandidate],
    canonical_topics: list[CanonicalTopic],
) -> list[GeneratedQuestion]:
    canonical_id_by_label = {
        topic.label: topic.canonical_topic_id for topic in canonical_topics
    }
    questions: list[GeneratedQuestion] = []
    for candidate in candidates:
        if len(candidate.relevant_topics) != 1:
            continue
        label = candidate.relevant_topics[0]
        questions.append(
            GeneratedQuestion(
                question_id=candidate.candidate_id,
                relevant_topics=candidate.relevant_topics,
                source_topic_ids=[canonical_id_by_label.get(label, label)],
                family=candidate.family,
                pattern=candidate.pattern,
                question_text=candidate.question_text,
                generation_scope="single_topic",
            )
        )
    return questions


def _pairwise_questions_from_candidates(
    candidates: list[QuestionCandidate],
) -> list[GeneratedQuestion]:
    questions: list[GeneratedQuestion] = []
    for candidate in candidates:
        if len(candidate.relevant_topics) < 2:
            continue
        pair_key = "__".join(candidate.relevant_topics)
        questions.append(
            GeneratedQuestion(
                question_id=candidate.candidate_id,
                relevant_topics=candidate.relevant_topics,
                source_pair_id=f"pair::{pair_key}",
                family=candidate.family,
                pattern=candidate.pattern,
                question_text=candidate.question_text,
                generation_scope="pairwise",
            )
        )
    return questions


def _validation_records_from_repairs(
    repairs: list[QuestionRepair],
    candidates: list[QuestionCandidate],
) -> list[QuestionValidationRecord]:
    by_id = {candidate.candidate_id: candidate for candidate in candidates}
    validations: list[QuestionValidationRecord] = []
    for repair in repairs:
        candidate = by_id[repair.candidate_id]
        validations.append(
            QuestionValidationRecord(
                question_id=repair.candidate_id,
                relevant_topics=candidate.relevant_topics,
                status=repair.status,
                original_text=repair.original_text,
                final_text=repair.final_text,
                reject_reason=repair.reject_reason,
                question_family=candidate.family,
            )
        )
    return validations
