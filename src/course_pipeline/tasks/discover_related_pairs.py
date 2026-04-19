from __future__ import annotations

from itertools import combinations

from course_pipeline.schemas import CanonicalTopic, RelatedTopicPair, TopicEvidence


WRAPPER_TYPES = {
    "chapter_wrapper",
    "example_block",
    "case_study_container",
    "wrapper_or_container_candidate",
}


def discover_related_pairs(canonical_topics: list[CanonicalTopic]) -> list[RelatedTopicPair]:
    pairs: list[RelatedTopicPair] = []

    for left, right in combinations(canonical_topics, 2):
        if left.topic_type in WRAPPER_TYPES or right.topic_type in WRAPPER_TYPES:
            continue

        evidence = _pair_evidence(left, right)
        if not evidence:
            continue

        relation_type = _relation_type(left, right, evidence)
        pairs.append(
            RelatedTopicPair(
                pair_id=f"p_{len(pairs)+1:03d}",
                topic_x=left.label,
                topic_y=right.label,
                relation_type=relation_type,
                evidence_spans=evidence,
                confidence=0.82 if relation_type == "paired_scope" else 0.7,
            )
        )

    return pairs


def _pair_evidence(left: CanonicalTopic, right: CanonicalTopic) -> list[TopicEvidence]:
    evidence: list[TopicEvidence] = []
    for left_span in left.evidence:
        for right_span in right.evidence:
            if left_span.source != right_span.source:
                continue
            if left_span.text != right_span.text:
                continue
            text_low = left_span.text.lower()
            if (
                left.label.lower() in text_low and right.label.lower() in text_low
            ) or " and " in text_low:
                evidence.append(left_span)
    if evidence:
        return evidence

    for span in left.evidence + right.evidence:
        text_low = span.text.lower()
        if left.label.lower() in text_low and right.label.lower() in text_low:
            evidence.append(span)

    return _dedupe_evidence(evidence)


def _relation_type(
    left: CanonicalTopic,
    right: CanonicalTopic,
    evidence: list[TopicEvidence],
) -> str:
    left_label = left.label.lower()
    right_label = right.label.lower()
    for span in evidence:
        text_low = span.text.lower()
        if (
            f"{left_label} and {right_label}" in text_low
            or f"{right_label} and {left_label}" in text_low
        ):
            return "paired_scope"
        if " and " in text_low:
            return "paired_scope"
        if any(token in text_low for token in ("compare", "versus", "vs", "instead of")):
            return "explicit_comparison"
    return "shared_local_evidence"


def _dedupe_evidence(evidence: list[TopicEvidence]) -> list[TopicEvidence]:
    seen: set[tuple[str, str]] = set()
    deduped: list[TopicEvidence] = []
    for span in evidence:
        key = (span.source, span.text)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(span)
    return deduped
