from __future__ import annotations

from pathlib import Path

from course_pipeline.io_utils import read_jsonl, write_jsonl
from course_pipeline.schemas import GeneratedQuestion, NormalizedCourse, SemanticQuestion
from course_pipeline.tasks.build_course_context import build_course_context_frame
from course_pipeline.tasks.build_question_context import (
    build_question_context_frame,
    build_question_context_frames,
)


def _course() -> NormalizedCourse:
    return NormalizedCourse(
        course_id="24373",
        title="Intro to Data Science in Python",
        summary="Learn pandas and matplotlib for beginner data analysis.",
        overview=(
            "This course teaches pandas for tabular data analysis and matplotlib "
            "for simple plots."
        ),
        chapters=[
            {
                "chapter_index": 1,
                "title": "Introduction",
                "summary": "Course setup and orientation.",
                "source": "syllabus",
                "confidence": 1.0,
            },
            {
                "chapter_index": 2,
                "title": "Using pandas",
                "summary": "Load and inspect tabular data with pandas.",
                "source": "syllabus",
                "confidence": 1.0,
            },
            {
                "chapter_index": 3,
                "title": "Plotting with Matplotlib",
                "summary": "Make simple plots with matplotlib.",
                "source": "syllabus",
                "confidence": 1.0,
            },
        ],
        metadata={"level": "beginner", "subjects": ["data science", "python"]},
    )


def test_build_question_context_frame_maps_intent_and_chapter_scope() -> None:
    course = _course()
    course_context = build_course_context_frame(course)
    question = SemanticQuestion.model_validate(
        {
            "question_id": "24373:q:0012",
            "question_text": "What is pandas?",
            "question_family": "what_is",
            "relevant_topics": ["pandas", "tabular data"],
            "question_scope": "single_topic",
            "rationale": "Natural entry question.",
            "source_refs": ["chapter:2"],
        }
    )

    frame = build_question_context_frame(
        course=course,
        question=question,
        course_context_frame=course_context,
    )

    assert frame.question_intent == "definition"
    assert frame.chapter_scope == ["Using pandas"]
    assert frame.expected_answer_shape[0] == "short definition"
    assert "summary" in frame.support_refs
    assert "chapter_2" in frame.support_refs


def test_build_question_context_frame_handles_generated_comparison_question() -> None:
    course = _course()
    course_context = build_course_context_frame(course)
    question = GeneratedQuestion.model_validate(
        {
            "question_id": "24373:q:0044",
            "relevant_topics": ["pandas", "matplotlib"],
            "family": "what_is_the_difference_between_x_and_y",
            "pattern": "semantic_stage",
            "question_text": "What is the difference between pandas and matplotlib?",
            "generation_scope": "pairwise",
        }
    )

    frame = build_question_context_frame(
        course=course,
        question=question,
        course_context_frame=course_context,
    )

    assert frame.question_intent == "comparison"
    assert frame.expected_answer_shape[0] == "key difference"
    assert any("contrast" in item for item in frame.scope_bias)


def test_build_question_context_frames_can_emit_jsonl(tmp_path: Path) -> None:
    course = _course()
    course_context = build_course_context_frame(course)
    questions = [
        {
            "question_id": "24373:q:0012",
            "question_text": "What is pandas?",
            "question_family": "what_is",
            "relevant_topics": ["pandas"],
            "question_scope": "single_topic",
            "rationale": "Natural entry question.",
            "source_refs": ["chapter:2"],
        },
        {
            "question_id": "24373:q:0013",
            "question_text": "What is matplotlib used for?",
            "question_family": "what_is_it_used_for",
            "relevant_topics": ["matplotlib"],
            "question_scope": "single_topic",
            "rationale": "Natural usage question.",
            "source_refs": ["chapter:3"],
        },
    ]

    frames = build_question_context_frames(
        course=course,
        questions=questions,
        course_context_frame=course_context,
    )

    output_path = tmp_path / "question_context_frames.jsonl"
    write_jsonl(output_path, [item.model_dump(mode="json") for item in frames])
    rows = read_jsonl(output_path)

    assert len(rows) == 2
    assert rows[0]["course_id"] == "24373"
    assert rows[1]["question_intent"] == "usage"
