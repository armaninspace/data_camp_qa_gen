from __future__ import annotations

import re

from course_pipeline.schemas import NormalizedCourse, Topic, TopicEvidence


GENERIC_HEADINGS = {
    "common data problems",
    "advanced data problems",
    "introduction",
    "overview",
    "case study",
    "putting it all together",
}
HEADING_LIKE_PREFIXES = (
    "introduction to ",
    "working with ",
    "better code with ",
    "some simple ",
    "putting it all together",
    "case study",
)
ALWAYS_REJECT_TOPICS = {
    "case study",
    "putting it all together",
    "some simple time series",
    "better code with purrr",
}
LEXICAL_TOPICS = [
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
TOOL_LABELS = {
    "compose",
    "negate",
    "partial",
    "safely",
    "possibly",
    "compact",
    "where",
    "having",
    "distinct",
    "union",
    "indexes",
    "execution plans",
}
METRIC_LABELS = {
    "correlation",
    "autocorrelation",
}
TEST_LABELS = {
    "hypothesis testing",
}
SUMMARY_PATTERNS = [
    r"\b(white noise)\b",
    r"\b(random walk)\b",
    r"\b(correlation)\b",
    r"\b(autocorrelation)\b",
    r"\b(cointegration models?)\b",
    r"\b(lambda functions?)\b",
    r"\b(predicates)\b",
    r"\b(adverbs)\b",
    r"\b(list-columns)\b",
    r"\b(compose)\(\)",
    r"\b(negate)\(\)",
    r"\b(partial)\(\)",
    r"\b(safely)\(\)",
    r"\b(possibly)\(\)",
    r"\b(compact)\(\)",
    r"\b(indexes)\b",
    r"\b(execution plans?)\b",
    r"\b(query processing order)\b",
    r"\b(statistics time)\b",
    r"\b(statistics io)\b",
    r"\b(where)\b",
    r"\b(having)\b",
    r"\b(distinct)\b",
    r"\b(union)\b",
    r"\b(sub-queries)\b",
]


def _simple_topic_id(i: int) -> str:
    return f"t{i:03d}"


def _clean_label(text: str) -> str:
    label = text.strip(" .,:;").lower()
    label = re.sub(r"\s+", " ", label)
    return label


def _split_coordinated_phrase(text: str) -> list[str]:
    parts = re.split(r"\band\b", text, flags=re.IGNORECASE)
    cleaned = [_clean_label(p) for p in parts if p.strip()]
    if len(cleaned) == 2:
        left_words = cleaned[0].split()
        right_words = cleaned[1].split()
        if len(left_words) == 1 and len(right_words) > 1:
            cleaned[0] = f"{cleaned[0]} {' '.join(right_words[1:])}"
    return cleaned if len(cleaned) > 1 else []


def _is_heading_like(label: str) -> bool:
    return label in ALWAYS_REJECT_TOPICS or label.startswith(HEADING_LIKE_PREFIXES)


def is_heading_like_topic(label: str) -> bool:
    return _is_heading_like(_clean_label(label))


def _add_topic(
    topics: list[Topic],
    seen: set[str],
    *,
    label: str,
    source: str,
    evidence_text: str,
    confidence: float,
    topic_type: str = "concept",
) -> None:
    clean = _clean_label(label)
    if not clean or clean in seen or clean in GENERIC_HEADINGS or clean in ALWAYS_REJECT_TOPICS:
        return
    seen.add(clean)
    topics.append(
        Topic(
            topic_id=_simple_topic_id(len(topics) + 1),
            label=clean,
            topic_type=topic_type,
            description=f"Topic extracted from {source}: {clean}",
            evidence=[TopicEvidence(source=source, text=evidence_text)],
            confidence=confidence,
        )
    )


def _extract_summary_topics(summary: str) -> list[str]:
    found: list[str] = []
    text = summary.lower()
    for pattern in SUMMARY_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            label = _clean_label(match.group(1))
            if label not in found:
                found.append(label)
    return found


def _infer_topic_type(label: str) -> str:
    if label in METRIC_LABELS:
        return "metric"
    if label in TEST_LABELS:
        return "test"
    if label in TOOL_LABELS:
        return "tool"
    if "function" in label or "functions" in label:
        return "tool"
    if label.endswith("models") or label.endswith("model"):
        return "concept"
    if "query processing order" in label:
        return "procedure"
    return "concept"


def extract_atomic_topics_baseline(course: NormalizedCourse) -> list[Topic]:
    topics: list[Topic] = []
    seen: set[str] = set()

    for chapter in course.chapters:
        heading = _clean_label(chapter.title)
        split_parts = _split_coordinated_phrase(heading)
        summary_text = chapter.summary or ""

        if split_parts:
            for label in split_parts:
                _add_topic(
                    topics,
                    seen,
                    label=label,
                    source=chapter.source,
                    evidence_text=chapter.title,
                    confidence=0.75,
                    topic_type=_infer_topic_type(label),
                )
        elif not _is_heading_like(heading):
            _add_topic(
                topics,
                seen,
                label=heading,
                source=chapter.source,
                evidence_text=chapter.title,
                confidence=0.55,
                topic_type=_infer_topic_type(heading),
            )

        for label in _extract_summary_topics(summary_text):
            _add_topic(
                topics,
                seen,
                label=label,
                source=chapter.source,
                evidence_text=summary_text,
                confidence=0.8,
                topic_type=_infer_topic_type(label),
            )

    overview = ((course.overview or "") + " " + (course.summary or "")).lower()
    for item in LEXICAL_TOPICS:
        if item in overview:
            _add_topic(
                topics,
                seen,
                label=item,
                source="overview",
                evidence_text=item,
                confidence=0.75,
                topic_type=_infer_topic_type(item),
            )

    return topics
