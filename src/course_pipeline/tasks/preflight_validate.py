from __future__ import annotations

from pathlib import Path
from typing import Any

from course_pipeline.schemas import ExcludedCourseRecord


BROKEN_TITLES = {
    "untitled course",
    "www.classcentral.com",
}


def preflight_validate_course(raw: dict[str, Any], source_path: str | Path) -> ExcludedCourseRecord | None:
    title_raw = raw.get("title")
    title = str(title_raw).strip() if title_raw is not None else None
    overview = raw.get("overview")
    syllabus = raw.get("syllabus")
    syllabus_count = len(syllabus) if isinstance(syllabus, list) else 0
    overview_present = bool(str(overview).strip()) if overview is not None else False

    source_url = str(raw.get("source_url") or raw.get("final_url") or "").strip()
    course_id = _course_id(raw, source_url, title)

    if not title or title.lower() in BROKEN_TITLES:
        return ExcludedCourseRecord(
            course_id=course_id,
            source_path=str(source_path),
            quality_status="broken",
            exclude_reason="malformed_title",
            title_raw=title,
            overview_present=overview_present,
            syllabus_count=syllabus_count,
        )

    if not overview_present and syllabus_count == 0:
        return ExcludedCourseRecord(
            course_id=course_id,
            source_path=str(source_path),
            quality_status="broken",
            exclude_reason="no_usable_content",
            title_raw=title,
            overview_present=overview_present,
            syllabus_count=syllabus_count,
        )

    return None


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
