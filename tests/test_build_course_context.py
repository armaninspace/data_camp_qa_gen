from __future__ import annotations

from pathlib import Path

from course_pipeline.io_utils import read_jsonl, write_jsonl
from course_pipeline.schemas import NormalizedCourse, SemanticStageResult
from course_pipeline.tasks.build_course_context import (
    build_course_context_frame,
    build_course_context_frames,
)


def _course(course_id: str, title: str, level: str, subjects: list[str]) -> NormalizedCourse:
    return NormalizedCourse(
        course_id=course_id,
        title=title,
        summary="Learn pandas and matplotlib to load data, filter rows, and make plots.",
        overview=(
            "This course teaches learners how to load data, inspect tabular data, "
            "filter rows, and make simple plots with pandas and matplotlib."
        ),
        chapters=[
            {
                "chapter_index": 1,
                "title": "Using pandas",
                "summary": "Load and inspect tabular data.",
                "source": "syllabus",
                "confidence": 1.0,
            },
            {
                "chapter_index": 2,
                "title": "Plotting with Matplotlib",
                "summary": "Make simple plots.",
                "source": "syllabus",
                "confidence": 1.0,
            },
        ],
        metadata={"level": level, "subjects": subjects},
    )


def _semantic_result() -> SemanticStageResult:
    return SemanticStageResult.model_validate(
        {
            "topics": [
                {
                    "label": "pandas",
                    "normalized_label": "pandas",
                    "topic_type": "tool",
                    "confidence": 0.95,
                    "course_centrality": 0.9,
                    "source_refs": ["overview"],
                    "rationale": "Central tool.",
                },
                {
                    "label": "matplotlib",
                    "normalized_label": "matplotlib",
                    "topic_type": "tool",
                    "confidence": 0.93,
                    "course_centrality": 0.84,
                    "source_refs": ["overview"],
                    "rationale": "Central plotting tool.",
                },
                {
                    "label": "filter rows",
                    "normalized_label": "filter rows",
                    "topic_type": "procedure",
                    "confidence": 0.82,
                    "course_centrality": 0.8,
                    "source_refs": ["chapter:1"],
                    "rationale": "Core procedure.",
                },
            ],
            "correlated_topics": [],
            "topic_questions": [],
            "correlated_topic_questions": [],
            "synthetic_answers": [],
        }
    )


def test_build_course_context_frame_has_stable_machine_shape() -> None:
    frame = build_course_context_frame(
        _course("24373", "Intro to Data Science in Python", "beginner", ["data science", "python"]),
        _semantic_result(),
    )

    assert frame.course_id == "24373"
    assert frame.course_title == "Intro to Data Science in Python"
    assert frame.learner_level == "beginner"
    assert frame.domain == "data science in python"
    assert frame.primary_tools[:2] == ["pandas", "Matplotlib"]
    assert "filter rows" in frame.core_tasks
    assert frame.answer_style.depth == "introductory"
    assert frame.answer_style.keep_short is True
    assert any("beginner explanations" in item for item in frame.scope_bias)


def test_build_course_context_frame_differs_across_courses() -> None:
    python_frame = build_course_context_frame(
        _course("24373", "Intro to Data Science in Python", "beginner", ["data science", "python"]),
        _semantic_result(),
    )
    sql_course = NormalizedCourse(
        course_id="24516",
        title="Improving Query Performance in SQL Server",
        summary="Learn SQL Server query tuning and execution plans.",
        overview="This course teaches query tuning, indexes, and execution plans in SQL Server.",
        chapters=[],
        metadata={"level": "intermediate", "subjects": ["sql", "performance"]},
    )
    sql_frame = build_course_context_frame(sql_course, None)

    assert python_frame.course_id != sql_frame.course_id
    assert python_frame.domain != sql_frame.domain
    assert python_frame.primary_tools != sql_frame.primary_tools
    assert python_frame.answer_style.depth != sql_frame.answer_style.depth


def test_build_course_context_frames_can_emit_jsonl(tmp_path: Path) -> None:
    frames = build_course_context_frames(
        [
            _course("24373", "Intro to Data Science in Python", "beginner", ["data science", "python"]),
            _course("24511", "Data Manipulation with pandas", "intermediate", ["data analysis", "python"]),
        ],
        {"24373": _semantic_result()},
    )

    output_path = tmp_path / "course_context_frames.jsonl"
    write_jsonl(output_path, [item.model_dump(mode="json") for item in frames])
    rows = read_jsonl(output_path)

    assert len(rows) == 2
    assert rows[0]["course_id"] == "24373"
    assert "course_title" in rows[1]
