from __future__ import annotations

import re

from course_pipeline.schemas import (
    AnswerStyle,
    CourseContextFrame,
    NormalizedCourse,
    SemanticStageResult,
)


KNOWN_TOOL_LABELS = {
    "python": "Python",
    "r": "R",
    "sql": "SQL",
    "sql server": "SQL Server",
    "pandas": "pandas",
    "matplotlib": "Matplotlib",
    "numpy": "NumPy",
    "purrr": "purrr",
    "dplyr": "dplyr",
}
COMMON_TASK_PATTERNS = (
    ("load data", r"\bload data\b|\bimport data\b"),
    ("inspect tabular data", r"\binspect\b|\bexplore\b|\btabular data\b"),
    ("filter rows", r"\bfilter\b|\bsubset\b"),
    ("make simple plots", r"\bplot\b|\bvisuali[sz]e\b"),
    ("basic analysis", r"\banalysis\b|\banalyze\b"),
    ("forecast time series", r"\bforecast\b|\btime series\b"),
)


def build_course_context_frame(
    course: NormalizedCourse,
    semantic_result: SemanticStageResult | None = None,
) -> CourseContextFrame:
    learner_level = _infer_learner_level(course)
    return CourseContextFrame(
        course_id=course.course_id,
        course_title=course.title,
        learner_level=learner_level,
        domain=_infer_domain(course),
        primary_tools=_infer_primary_tools(course, semantic_result),
        core_tasks=_infer_core_tasks(course, semantic_result),
        scope_bias=_infer_scope_bias(course, semantic_result, learner_level),
        answer_style=_infer_answer_style(learner_level),
    )


def build_course_context_frames(
    courses: list[NormalizedCourse],
    semantic_results_by_course_id: dict[str, SemanticStageResult] | None = None,
) -> list[CourseContextFrame]:
    semantic_results_by_course_id = semantic_results_by_course_id or {}
    return [
        build_course_context_frame(
            course,
            semantic_results_by_course_id.get(course.course_id),
        )
        for course in courses
    ]


def _infer_learner_level(course: NormalizedCourse) -> str | None:
    level = str(course.metadata.get("level") or "").strip().lower()
    return level or None


def _infer_domain(course: NormalizedCourse) -> str:
    subjects = [
        str(item).strip().lower()
        for item in course.metadata.get("subjects", [])
        if str(item).strip()
    ]
    if subjects:
        return " in ".join(dict.fromkeys(subjects[:2]))

    title = course.title.strip().lower()
    if title:
        return title

    return "general course context"


def _infer_primary_tools(
    course: NormalizedCourse,
    semantic_result: SemanticStageResult | None,
) -> list[str]:
    tools: list[str] = []
    if semantic_result is not None:
        for topic in semantic_result.topics:
            if topic.topic_type == "tool":
                tools.append(_display_tool_label(topic.label))

    combined_text = " ".join(
        filter(
            None,
            [
                course.title,
                course.summary,
                course.overview,
                *[chapter.title for chapter in course.chapters],
                *[chapter.summary for chapter in course.chapters if chapter.summary],
            ],
        )
    ).lower()
    for pattern, display in KNOWN_TOOL_LABELS.items():
        if re.search(rf"\b{re.escape(pattern)}\b", combined_text):
            tools.append(display)

    return list(dict.fromkeys(tools))


def _infer_core_tasks(
    course: NormalizedCourse,
    semantic_result: SemanticStageResult | None,
) -> list[str]:
    tasks: list[str] = []
    if semantic_result is not None:
        for topic in semantic_result.topics:
            if topic.topic_type == "procedure":
                tasks.append(topic.normalized_label)

    combined_text = " ".join(
        filter(
            None,
            [
                course.summary,
                course.overview,
                *[chapter.title for chapter in course.chapters],
                *[chapter.summary for chapter in course.chapters if chapter.summary],
            ],
        )
    ).lower()
    for label, pattern in COMMON_TASK_PATTERNS:
        if re.search(pattern, combined_text):
            tasks.append(label)

    return list(dict.fromkeys(tasks))


def _infer_scope_bias(
    course: NormalizedCourse,
    semantic_result: SemanticStageResult | None,
    learner_level: str | None,
) -> list[str]:
    bias: list[str] = []
    if learner_level == "beginner":
        bias.append("favor beginner explanations")
    elif learner_level == "intermediate":
        bias.append("favor intermediate explanations")
    elif learner_level:
        bias.append(f"match {learner_level} course depth")

    tools = _infer_primary_tools(course, semantic_result)
    if tools:
        bias.append(f"favor {', '.join(tools[:3])} examples")

    domain = _infer_domain(course)
    if domain:
        bias.append(f"answer within {domain}")

    bias.append("avoid unrelated advanced detail unless course context supports it")
    return list(dict.fromkeys(bias))


def _infer_answer_style(learner_level: str | None) -> AnswerStyle:
    if learner_level == "beginner":
        return AnswerStyle(
            depth="introductory",
            tone="direct and instructional",
            prefer_examples=True,
            prefer_definitions=True,
            keep_short=True,
        )
    if learner_level == "intermediate":
        return AnswerStyle(
            depth="intermediate",
            tone="direct and instructional",
            prefer_examples=True,
            prefer_definitions=False,
            keep_short=True,
        )
    return AnswerStyle(
        depth="general",
        tone="direct and instructional",
        prefer_examples=True,
        prefer_definitions=True,
        keep_short=True,
    )


def _display_tool_label(label: str) -> str:
    normalized = label.strip().lower()
    return KNOWN_TOOL_LABELS.get(normalized, label)
