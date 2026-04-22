
from __future__ import annotations

from pathlib import Path
import json
import re
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


def _coerce_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _fallback_title(raw: dict) -> str:
    title = _coerce_text(raw.get("title"))
    if title and not title.startswith("www."):
        return title
    source_url = _coerce_text(raw.get("source_url")) or _coerce_text(raw.get("final_url"))
    if source_url:
        slug = source_url.rstrip("/").split("/")[-1]
        slug = re.sub(r"^\w+-", "", slug)
        return slug.replace("-", " ").strip() or "Untitled course"
    return "Untitled course"


def _fallback_course_id(raw: dict, title: str) -> str:
    direct = _coerce_text(raw.get("course_id") or raw.get("id") or raw.get("slug"))
    if direct:
        return direct
    for field in ("source_url", "final_url"):
        value = _coerce_text(raw.get(field))
        if not value:
            continue
        match = re.search(r"-(\d+)(?:$|/)", value)
        if match:
            return match.group(1)
    return title


def normalize_course_record(raw: dict) -> NormalizedCourse:
    title = _fallback_title(raw)
    course_id = _fallback_course_id(raw, title)

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
        inferred = _infer_overview_chapters(_coerce_text(raw.get("overview")) or "")
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
        title=title,
        provider=_coerce_text(raw.get("provider"))
        or _coerce_text(details.get("provider"))
        or _coerce_text(raw.get("school")),
        summary=_coerce_text(raw.get("summary")),
        overview=_coerce_text(raw.get("overview")),
        chapters=chapters,
        metadata={
            "level": _coerce_text(details.get("level")),
            "duration_hours": _coerce_text(details.get("duration_hours"))
            or _coerce_text(details.get("duration_workload")),
            "subjects": raw.get("subjects", []),
        },
        source_refs={
            "title": "title" in raw,
            "summary": "summary" in raw,
            "overview": "overview" in raw,
            "syllabus": "syllabus" in raw,
            "source_url": "source_url" in raw,
            "final_url": "final_url" in raw,
        },
    )


def _infer_overview_chapters(overview: str) -> list[str]:
    inferred: list[str] = []
    for paragraph in re.split(r"\n\s*\n", overview):
        label = " ".join(line.strip() for line in paragraph.splitlines() if line.strip())
        if _is_heading_like_overview_paragraph(label):
            inferred.append(label)
    return inferred


def _is_heading_like_overview_paragraph(text: str) -> bool:
    if not text:
        return False
    if len(text) > 60:
        return False
    if any(char in text for char in ".!?"):
        return False
    words = text.split()
    if len(words) < 2 or len(words) > 8:
        return False
    stopwords = {"the", "and", "of", "to", "with", "for", "in", "on", "a", "an"}
    title_like_words = sum(word[:1].isupper() or word.lower() in stopwords for word in words)
    return title_like_words >= max(2, len(words) - 1)
