from __future__ import annotations

from pathlib import Path

import pytest

from course_pipeline.io_utils import write_jsonl
from course_pipeline.schemas import (
    AnswerRecord,
    CanonicalTopic,
    GeneratedQuestion,
    LedgerRow,
    NormalizedCourse,
    QuestionValidationRecord,
    Topic,
    TopicEvidence,
)
from course_pipeline.tasks.render import (
    persist_stage_artifacts,
    rebuild_run_summary,
    validate_rendered_output_consistency,
)


def _course(course_id: str, title: str) -> NormalizedCourse:
    return NormalizedCourse(course_id=course_id, title=title)


def _topic(topic_id: str, label: str) -> Topic:
    return Topic(
        topic_id=topic_id,
        label=label,
        description=label,
        evidence=[TopicEvidence(source="test", text=label)],
    )


def _canonical(label: str, topic_id: str) -> CanonicalTopic:
    return CanonicalTopic(
        canonical_topic_id=f"ct_{topic_id}",
        label=label,
        aliases=[label],
        member_topic_ids=[topic_id],
    )


def _question(candidate_id: str, label: str) -> GeneratedQuestion:
    return GeneratedQuestion(
        question_id=candidate_id,
        relevant_topics=[label],
        source_topic_ids=[f"ct_{label}"],
        family="entry",
        pattern="What is {x}?",
        question_text=f"What is {label}?",
        generation_scope="single_topic",
    )


def _validation(candidate_id: str, label: str, text: str) -> QuestionValidationRecord:
    return QuestionValidationRecord(
        question_id=candidate_id,
        relevant_topics=[label],
        status="accepted",
        original_text=text,
        final_text=text,
        question_family="entry",
    )


def _answer(candidate_id: str, text: str) -> AnswerRecord:
    return AnswerRecord(
        question_id=candidate_id,
        question_text=text,
        answer_text="answer",
        correctness="correct",
        confidence=1.0,
    )


def _row(course_id: str, title: str, text: str) -> LedgerRow:
    return LedgerRow(
        row_id=f"row_{course_id}",
        course={"course_id": course_id, "title": title},
        relevant_topics=["topic"],
        question_text=text,
        question_answer="answer",
        correctness="correct",
        question_family="entry",
        status="answered",
    )


def test_persist_stage_artifacts_upserts_by_course_id(tmp_path: Path) -> None:
    output_dir = tmp_path / "run"

    persist_stage_artifacts(
        output_dir=output_dir,
        course=_course("1", "One"),
        topics=[_topic("t1", "topic one")],
        canonical_topics=[_canonical("topic one", "t1")],
        single_topic_questions=[_question("q1", "topic one")],
        validations=[_validation("q1", "topic one", "What is topic one?")],
        answers=[_answer("q1", "What is topic one?")],
        rows=[_row("1", "One", "What is topic one?")],
    )
    persist_stage_artifacts(
        output_dir=output_dir,
        course=_course("1", "One Updated"),
        topics=[_topic("t1b", "topic one updated")],
        canonical_topics=[_canonical("topic one updated", "t1b")],
        single_topic_questions=[_question("q1b", "topic one updated")],
        validations=[_validation("q1b", "topic one updated", "What is topic one updated?")],
        answers=[_answer("q1b", "What is topic one updated?")],
        rows=[_row("1", "One Updated", "What is topic one updated?")],
    )
    persist_stage_artifacts(
        output_dir=output_dir,
        course=_course("2", "Two"),
        topics=[_topic("t2", "topic two")],
        canonical_topics=[_canonical("topic two", "t2")],
        single_topic_questions=[_question("q2", "topic two")],
        validations=[_validation("q2", "topic two", "What is topic two?")],
        answers=[_answer("q2", "What is topic two?")],
        rows=[_row("2", "Two", "What is topic two?")],
    )

    summary = rebuild_run_summary(output_dir)

    assert summary["course_count"] == 2
    assert summary["artifact_counts"]["semantic_topics.jsonl"] == 0
    assert summary["artifact_counts"]["semantic_review_decisions.jsonl"] == 0
    assert summary["artifact_counts"]["canonical_topics.jsonl"] == 2
    assert summary["artifact_counts"]["vetted_topics.jsonl"] == 2
    assert summary["artifact_counts"]["single_topic_questions.jsonl"] == 2
    assert "synthetic_answer_count" in summary
    assert "synthetic_accepted_count" in summary
    assert "synthetic_rewrite_count" in summary
    assert "synthetic_reject_count" in summary
    assert "rejected_question_count" in summary
    assert "errored_question_count" in summary
    assert "quality_metrics" in summary
    assert "reject_rate" in summary["quality_metrics"]
    assert "entry_question_count" in summary["quality_metrics"]
    bundle = (output_dir / "course_yaml" / "1.yaml").read_text(encoding="utf-8")
    assert "One Updated" in bundle
    assert "single_topic_questions" in bundle


def test_rebuild_run_summary_uses_shared_rows_and_keeps_zero_row_courses(tmp_path: Path) -> None:
    output_dir = tmp_path / "run"

    persist_stage_artifacts(
        output_dir=output_dir,
        course=_course("1", "One"),
        topics=[_topic("t1", "matplotlib")],
        canonical_topics=[_canonical("matplotlib", "t1")],
        single_topic_questions=[_question("q1", "matplotlib")],
        validations=[_validation("q1", "matplotlib", "What is matplotlib?")],
        answers=[_answer("q1", "What is matplotlib?")],
        rows=[_row("1", "One", "What is matplotlib?")],
    )
    persist_stage_artifacts(
        output_dir=output_dir,
        course=_course("2", "Two"),
        topics=[],
        canonical_topics=[],
        single_topic_questions=[],
        validations=[],
        answers=[],
        rows=[],
    )

    summary = rebuild_run_summary(output_dir)

    assert summary["course_count"] == 2
    assert summary["answered_count"] == 1
    course_counts = {item["course_id"]: item for item in summary["courses"]}
    assert course_counts["1"]["row_count"] == 1
    assert course_counts["1"]["shared_answer_count"] == 1
    assert course_counts["2"]["row_count"] == 0
    assert course_counts["2"]["shared_answer_count"] == 0


def test_rendered_output_consistency_fails_when_bundle_rows_are_missing_from_shared_artifacts(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "run"

    persist_stage_artifacts(
        output_dir=output_dir,
        course=_course("1", "One"),
        topics=[_topic("t1", "matplotlib")],
        canonical_topics=[_canonical("matplotlib", "t1")],
        single_topic_questions=[_question("q1", "matplotlib")],
        validations=[_validation("q1", "matplotlib", "What is matplotlib?")],
        answers=[_answer("q1", "What is matplotlib?")],
        rows=[_row("1", "One", "What is matplotlib?")],
    )

    write_jsonl(output_dir / "answers.jsonl", [])
    write_jsonl(output_dir / "all_rows.jsonl", [])

    with pytest.raises(RuntimeError, match="consistency check failed"):
        validate_rendered_output_consistency(output_dir)
