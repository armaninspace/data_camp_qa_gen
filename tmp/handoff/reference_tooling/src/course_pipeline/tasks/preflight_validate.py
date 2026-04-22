from __future__ import annotations

from pathlib import Path
from typing import Any

from course_pipeline.schemas import PreflightCourseDecision


BROKEN_TITLES = {
    "untitled course",
    "www.classcentral.com",
}
LOW_QUALITY_MARKETING_PHRASES = (
    "in just four hours",
    "we designed it for people with no",
    "market leader",
    "demand for data skills",
    "help you work more efficiently",
    "helping you understand common, everyday",
)


def preflight_validate_course(
    raw: dict[str, Any],
    source_path: str | Path,
) -> PreflightCourseDecision:
    title_raw = raw.get("title")
    title = str(title_raw).strip() if title_raw is not None else None
    overview = raw.get("overview")
    syllabus = raw.get("syllabus")
    syllabus_count = len(syllabus) if isinstance(syllabus, list) else 0
    overview_present = bool(str(overview).strip()) if overview is not None else False

    source_url = str(raw.get("source_url") or raw.get("final_url") or "").strip()
    course_id = _course_id(raw, source_url, title)

    if not title or title.lower() in BROKEN_TITLES:
        return PreflightCourseDecision(
            course_id=course_id,
            source_path=str(source_path),
            quality_status="broken",
            exclude_reason="malformed_title",
            title_raw=title,
            overview_present=overview_present,
            syllabus_count=syllabus_count,
        )

    if not overview_present and syllabus_count == 0:
        return PreflightCourseDecision(
            course_id=course_id,
            source_path=str(source_path),
            quality_status="broken",
            exclude_reason="no_usable_content",
            title_raw=title,
            overview_present=overview_present,
            syllabus_count=syllabus_count,
        )

    if syllabus_count == 0 and _is_low_quality_overview_only_source(raw):
        return PreflightCourseDecision(
            course_id=course_id,
            source_path=str(source_path),
            quality_status="broken",
            exclude_reason="low_quality_source",
            title_raw=title,
            overview_present=overview_present,
            syllabus_count=syllabus_count,
        )

    if overview_present and syllabus_count > 0:
        quality_status = "usable"
    else:
        quality_status = "partial"

    return PreflightCourseDecision(
        course_id=course_id,
        source_path=str(source_path),
        quality_status=quality_status,
        exclude_reason=None,
        title_raw=title,
        overview_present=overview_present,
        syllabus_count=syllabus_count,
    )


def _course_id(raw: dict[str, Any], source_url: str, title: str | None) -> str:
    for key in ("course_id", "id", "slug"):
        value = raw.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    if source_url:
        for part in reversed(source_url.rstrip("/").split("-")):
            if part.isdigit():
                return part
    return title or "unknown-course"


def _is_low_quality_overview_only_source(raw: dict[str, Any]) -> bool:
    overview = str(raw.get("overview") or "").lower()
    summary = str(raw.get("summary") or "").lower()
    combined = f"{summary}\n{overview}"
    if not combined.strip():
        return False

    marketing_hits = sum(phrase in combined for phrase in LOW_QUALITY_MARKETING_PHRASES)
    heading_hits = sum(
        paragraph.istitle()
        for paragraph in [
            item.strip()
            for item in overview.split("\n\n")
            if item.strip()
        ]
    )
    return marketing_hits >= 2 or (marketing_hits >= 1 and heading_hits >= 3)
