from __future__ import annotations

from course_pipeline.schemas import (
    CacheRow,
    CourseContextFrame,
    ProvidedContext,
    QuestionContextFrame,
    TrainRow,
)


def _course_context(course_id: str, title: str) -> CourseContextFrame:
    return CourseContextFrame.model_validate(
        {
            "course_id": course_id,
            "course_title": title,
            "learner_level": "beginner",
            "domain": "data science in python",
            "primary_tools": ["Python", "pandas"],
            "core_tasks": ["load data", "inspect tabular data"],
            "scope_bias": ["favor pandas examples", "keep explanations short"],
            "answer_style": {
                "depth": "introductory",
                "tone": "direct and instructional",
                "prefer_examples": True,
                "prefer_definitions": True,
                "keep_short": True,
            },
        }
    )


def _question_context(course_id: str, question_id: str) -> QuestionContextFrame:
    return QuestionContextFrame.model_validate(
        {
            "question_id": question_id,
            "course_id": course_id,
            "question_text": "What is pandas?",
            "question_intent": "definition",
            "relevant_topics": ["pandas", "tabular data"],
            "chapter_scope": ["Introduction", "Using pandas"],
            "expected_answer_shape": [
                "short definition",
                "why it matters in this course",
            ],
            "scope_bias": ["answer in Python data-analysis context"],
            "support_refs": ["overview", "chapter_2"],
        }
    )


def test_context_frames_round_trip_with_provided_context() -> None:
    provided = ProvidedContext(
        course_context_frame=_course_context("24373", "Intro to Data Science in Python"),
        question_context_frame=_question_context("24373", "24373:q:0012"),
    )

    payload = provided.model_dump(mode="json")

    assert payload["course_context_frame"]["course_id"] == "24373"
    assert payload["question_context_frame"]["question_intent"] == "definition"
    assert payload["course_context_frame"]["answer_style"]["keep_short"] is True


def test_train_row_preserves_course_bound_identity_and_dedupes_variants() -> None:
    row = TrainRow.model_validate(
        {
            "row_id": "24373:q:0012:a:1",
            "course_id": "24373",
            "question_id": "24373:q:0012",
            "question_text": "What is pandas?",
            "provided_context": {
                "course_context_frame": _course_context(
                    "24373", "Intro to Data Science in Python"
                ).model_dump(mode="json"),
                "question_context_frame": _question_context(
                    "24373", "24373:q:0012"
                ).model_dump(mode="json"),
            },
            "teacher_answer": "Pandas is a Python library for working with tabular data.",
            "question_variants": [
                "What is pandas?",
                "What does pandas do?",
                "What is pandas?",
            ],
            "answer_quality_flags": {
                "course_aligned": True,
                "train_eligible": True,
                "cache_eligible": False,
            },
        }
    )

    assert row.course_id == "24373"
    assert row.question_variants == ["What is pandas?", "What does pandas do?"]
    assert row.answer_quality_flags.train_eligible is True
    assert row.answer_quality_flags.cache_eligible is False


def test_cache_row_keeps_same_question_text_separate_across_courses() -> None:
    row_a = CacheRow.model_validate(
        {
            "cache_key": "24373::what is pandas",
            "course_id": "24373",
            "question_text": "What is pandas?",
            "question_variants": ["What is pandas?"],
            "provided_context": {
                "course_context_frame": _course_context(
                    "24373", "Intro to Data Science in Python"
                ).model_dump(mode="json"),
                "question_context_frame": _question_context(
                    "24373", "24373:q:0012"
                ).model_dump(mode="json"),
            },
            "canonical_answer": "Pandas is a Python library for tabular data.",
            "cache_eligible": True,
            "global_question_signature": "what is pandas",
        }
    )
    row_b = CacheRow.model_validate(
        {
            "cache_key": "24511::what is pandas",
            "course_id": "24511",
            "question_text": "What is pandas?",
            "question_variants": ["What is pandas?"],
            "provided_context": {
                "course_context_frame": _course_context(
                    "24511", "Data Analysis with pandas"
                ).model_dump(mode="json"),
                "question_context_frame": _question_context(
                    "24511", "24511:q:0003"
                ).model_dump(mode="json"),
            },
            "canonical_answer": "Pandas is used in this course for tabular data analysis in Python.",
            "cache_eligible": True,
            "global_question_signature": "what is pandas",
        }
    )

    assert row_a.question_text == row_b.question_text
    assert row_a.course_id != row_b.course_id
    assert row_a.cache_key != row_b.cache_key
    assert row_a.provided_context.course_context_frame.course_id != (
        row_b.provided_context.course_context_frame.course_id
    )
