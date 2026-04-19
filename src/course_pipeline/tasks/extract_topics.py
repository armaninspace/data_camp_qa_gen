
from __future__ import annotations

import re
from course_pipeline.schemas import NormalizedCourse, Topic, TopicEvidence


GENERIC_HEADINGS = {
    "common data problems",
    "advanced data problems",
    "introduction",
    "overview",
}


def _simple_topic_id(i: int) -> str:
    return f"t{i:03d}"


def _split_coordinated_phrase(text: str) -> list[str]:
    parts = re.split(r"\band\b", text, flags=re.IGNORECASE)
    cleaned = [p.strip(" .,:;").lower() for p in parts if p.strip()]
    return cleaned if len(cleaned) > 1 else []


def extract_atomic_topics_baseline(course: NormalizedCourse) -> list[Topic]:
    topics: list[Topic] = []
    seen: set[str] = set()

    for chapter in course.chapters:
        heading = chapter.title.strip().lower()
        split_parts = _split_coordinated_phrase(heading)
        candidates = split_parts if split_parts else [heading]

        for label in candidates:
            if label in GENERIC_HEADINGS:
                continue
            if label in seen:
                continue
            seen.add(label)
            topics.append(
                Topic(
                    topic_id=_simple_topic_id(len(topics) + 1),
                    label=label,
                    topic_type="concept",
                    description=f"Topic inferred from chapter heading: {label}",
                    evidence=[
                        TopicEvidence(
                            source=chapter.source,
                            text=chapter.title,
                        )
                    ],
                    confidence=0.55 if split_parts else 0.45,
                )
            )

    overview = ((course.overview or "") + " " + (course.summary or "")).lower()
    lexical = [
        "record linkage",
        "missing values",
        "duplicates",
        "data types",
        "range constraints",
        "category labels",
        "strings",
        "measurement units",
        "text data",
        "categorical data",
    ]
    for item in lexical:
        if item in overview and item not in seen:
            seen.add(item)
            topics.append(
                Topic(
                    topic_id=_simple_topic_id(len(topics) + 1),
                    label=item,
                    topic_type="concept",
                    description=f"Topic mined from course text: {item}",
                    evidence=[TopicEvidence(source="overview", text=item)],
                    confidence=0.75,
                )
            )

    return topics
