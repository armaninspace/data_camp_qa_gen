
from __future__ import annotations

from pathlib import Path
from course_pipeline.io_utils import append_jsonl, write_yaml
from course_pipeline.schemas import (
    AnswerRecord,
    CanonicalTopic,
    CourseBundle,
    LedgerRow,
    NormalizedCourse,
    QuestionCandidate,
    QuestionRepair,
    Topic,
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
    append_jsonl(out / "normalized_courses.jsonl", course)
    for topic in topics:
        append_jsonl(out / "topics.jsonl", {"course_id": course.course_id, **topic.model_dump()})
    for candidate in candidates:
        append_jsonl(
            out / "question_candidates.jsonl",
            {"course_id": course.course_id, **candidate.model_dump()},
        )
    for repair in repairs:
        append_jsonl(
            out / "question_repairs.jsonl",
            {"course_id": course.course_id, **repair.model_dump()},
        )
    for answer in answers:
        append_jsonl(
            out / "answers.jsonl",
            {"course_id": course.course_id, **answer.model_dump()},
        )
    for row in rows:
        append_jsonl(out / "all_rows.jsonl", row)

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
