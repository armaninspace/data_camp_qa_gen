
from __future__ import annotations

from pathlib import Path
import json
import yaml
from course_pipeline.schemas import Chapter, NormalizedCourse


def load_raw_course(path: str | Path) -> dict:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in {".yaml", ".yml", ".md"}:
        try:
            return yaml.safe_load(text)
        except Exception:
            return {"title": p.stem, "overview": text}
    return json.loads(text)


def normalize_course_record(raw: dict) -> NormalizedCourse:
    course_id = str(
        raw.get("course_id")
        or raw.get("id")
        or raw.get("slug")
        or raw.get("title", "course")
    )

    details = raw.get("details", {}) if isinstance(raw.get("details"), dict) else {}
    chapters: list[Chapter] = []

    syllabus = raw.get("syllabus") or []
    if isinstance(syllabus, list) and syllabus:
        for idx, item in enumerate(syllabus, start=1):
            if isinstance(item, dict):
                chapters.append(
                    Chapter(
                        chapter_index=idx,
                        title=str(item.get("title", f"Chapter {idx}")),
                        summary=item.get("summary"),
                        source="syllabus",
                        confidence=1.0,
                    )
                )
            else:
                chapters.append(
                    Chapter(
                        chapter_index=idx,
                        title=str(item),
                        summary=None,
                        source="syllabus",
                        confidence=1.0,
                    )
                )
    else:
        overview = raw.get("overview") or ""
        inferred = []
        for idx, line in enumerate(str(overview).splitlines(), start=1):
            line = line.strip()
            if line and len(line) < 80 and not line.endswith("."):
                inferred.append(line)
        for idx, title in enumerate(inferred[:8], start=1):
            chapters.append(
                Chapter(
                    chapter_index=idx,
                    title=title,
                    summary=None,
                    source="overview_inferred",
                    confidence=0.4,
                )
            )

    return NormalizedCourse(
        course_id=course_id,
        title=str(raw.get("title", "Untitled course")),
        provider=raw.get("provider") or raw.get("school"),
        summary=raw.get("summary"),
        overview=raw.get("overview"),
        chapters=chapters,
        metadata={
            "level": details.get("level"),
            "duration_hours": details.get("duration_hours")
            or details.get("duration_workload"),
            "subjects": raw.get("subjects", []),
        },
        source_refs={
            "title": "title" in raw,
            "summary": "summary" in raw,
            "overview": "overview" in raw,
            "syllabus": "syllabus" in raw,
        },
    )
