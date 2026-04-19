from __future__ import annotations

from pathlib import Path

import yaml

from course_pipeline.flows.course_question_pipeline import (
    SelectedCoursePath,
    preflight_validate_selected_paths,
)
from course_pipeline.tasks.preflight_validate import preflight_validate_course


def test_preflight_excludes_malformed_title() -> None:
    raw = {
        "title": "www.classcentral.com",
        "overview": None,
        "syllabus": [],
        "source_url": "https://www.classcentral.com/course/datacamp-bad-course-24650",
    }

    decision = preflight_validate_course(raw, "bad.yaml")

    assert decision.quality_status == "broken"
    assert decision.exclude_reason == "malformed_title"
    assert decision.course_id == "24650"


def test_preflight_excludes_missing_content() -> None:
    raw = {
        "title": "Some Course",
        "overview": None,
        "syllabus": [],
    }

    decision = preflight_validate_course(raw, "empty.yaml")

    assert decision.quality_status == "broken"
    assert decision.exclude_reason == "no_usable_content"


def test_preflight_marks_overview_only_course_partial() -> None:
    raw = {
        "course_id": "2",
        "title": "Partial Course",
        "overview": "Overview text only.",
        "syllabus": [],
    }

    decision = preflight_validate_course(raw, "partial.yaml")

    assert decision.quality_status == "partial"
    assert decision.exclude_reason is None


def test_preflight_marks_overview_and_syllabus_course_usable() -> None:
    raw = {
        "course_id": "3",
        "title": "Usable Course",
        "overview": "Overview text.",
        "syllabus": [{"title": "Chapter 1"}],
    }

    decision = preflight_validate_course(raw, "usable.yaml")

    assert decision.quality_status == "usable"
    assert decision.exclude_reason is None


def test_preflight_keeps_usable_course(tmp_path: Path) -> None:
    good = tmp_path / "good.yaml"
    bad = tmp_path / "bad.yaml"
    good.write_text(
        yaml.safe_dump(
            {
                "course_id": "1",
                "title": "Usable Course",
                "overview": "Short but usable overview.",
                "syllabus": [],
            }
        ),
        encoding="utf-8",
    )
    bad.write_text(
        yaml.safe_dump(
            {
                "source_url": "https://www.classcentral.com/course/datacamp-bad-course-24650",
                "title": "www.classcentral.com",
                "overview": None,
                "syllabus": [],
            }
        ),
        encoding="utf-8",
    )

    selection = preflight_validate_selected_paths.fn(
        [
            SelectedCoursePath(relative_path="good.yaml", absolute_path=str(good)),
            SelectedCoursePath(relative_path="bad.yaml", absolute_path=str(bad)),
        ]
    )

    assert [item.relative_path for item in selection.runnable_paths] == ["good.yaml"]
    assert [item.quality_status for item in selection.runnable_paths] == ["partial"]
    assert [item["exclude_reason"] for item in selection.excluded_rows] == ["malformed_title"]
    assert selection.quality_counts == {"usable": 0, "partial": 1, "broken": 1}
