from __future__ import annotations

from dataclasses import dataclass
import re

from course_pipeline.schemas import GeneratedQuestion, NormalizedCourse, SemanticTopic


ENTRY_FAMILY_BY_RUNTIME_FAMILY = {
    "what_is": "entry",
}


@dataclass(frozen=True)
class PolicyCoverageReport:
    detected_anchors: list[str]
    covered_anchors: list[str]
    missing_anchors: list[str]


def apply_post_semantic_policy(
    *,
    course: NormalizedCourse,
    semantic_topics: list[SemanticTopic],
    questions: list[GeneratedQuestion],
) -> tuple[list[GeneratedQuestion], PolicyCoverageReport]:
    anchors = _derive_anchor_labels(course, semantic_topics)
    updated_questions = [_canonicalize_question_family(question) for question in questions]

    covered: set[str] = set()
    for anchor in anchors:
        for index, question in enumerate(updated_questions):
            if question.generation_scope != "single_topic" or question.family != "entry":
                continue
            if not _question_matches_anchor(question.question_text, anchor):
                continue
            updated_questions[index] = question.model_copy(
                update={"required_entry": True, "anchor_label": anchor}
            )
            covered.add(anchor)
            break

    return updated_questions, PolicyCoverageReport(
        detected_anchors=anchors,
        covered_anchors=sorted(covered),
        missing_anchors=sorted(set(anchors) - covered),
    )


def enforce_required_entry_coverage(report: PolicyCoverageReport) -> None:
    return None


def _canonicalize_question_family(question: GeneratedQuestion) -> GeneratedQuestion:
    mapped_family = question.family
    if question.generation_scope == "single_topic":
        mapped_family = ENTRY_FAMILY_BY_RUNTIME_FAMILY.get(question.family, question.family)
    return question.model_copy(update={"family": mapped_family})


def _derive_anchor_labels(
    course: NormalizedCourse,
    semantic_topics: list[SemanticTopic],
) -> list[str]:
    if not _is_beginner_course(course):
        return []
    anchors: list[str] = []
    for topic in semantic_topics:
        if topic.topic_type not in {"concept", "tool"}:
            continue
        if topic.course_centrality < 0.8:
            continue
        anchors.append(topic.normalized_label)
    return list(dict.fromkeys(anchors))


def _is_beginner_course(course: NormalizedCourse) -> bool:
    level = str(course.metadata.get("level") or "").strip().lower()
    title = course.title.strip().lower()
    return (
        "beginner" in level
        or title.startswith("introduction")
        or title.startswith("intro ")
        or title.startswith("intro to ")
    )


def _question_matches_anchor(question_text: str, anchor_label: str) -> bool:
    normalized_question = _normalize_text(question_text)
    normalized_anchor = _normalize_text(anchor_label)
    anchor_variants = {normalized_anchor, _singularize(normalized_anchor)}
    return any(
        variant and re.search(rf"\b{re.escape(variant)}\b", normalized_question)
        for variant in anchor_variants
    )


def _normalize_text(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s]", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _singularize(label: str) -> str:
    if label.endswith("rices") and len(label) > 5:
        return label[:-3] + "x"
    if label.endswith("ies") and len(label) > 3:
        return label[:-3] + "y"
    if label.endswith("ices") and len(label) > 4:
        return label[:-4] + "ex"
    if label.endswith("ses") and len(label) > 3:
        return label[:-2]
    if label.endswith("s") and not label.endswith("ss") and len(label) > 1:
        return label[:-1]
    return label
