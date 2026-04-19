from __future__ import annotations

from course_pipeline.schemas import (
    CanonicalTopic,
    RelatedTopicPair,
    VettedTopic,
    VettedTopicPair,
)
from course_pipeline.tasks.extract_topics import is_heading_like_topic


WRAPPER_TYPES = {
    "chapter_wrapper",
    "example_block",
    "case_study_container",
    "wrapper_or_container_candidate",
}


def vet_topics_and_pairs(
    canonical_topics: list[CanonicalTopic],
    related_pairs: list[RelatedTopicPair],
) -> tuple[list[VettedTopic], list[VettedTopicPair]]:
    vetted_topics = _vet_topics(canonical_topics)
    vetted_pairs = _vet_pairs(related_pairs, vetted_topics)
    return vetted_topics, vetted_pairs


def _vet_topics(canonical_topics: list[CanonicalTopic]) -> list[VettedTopic]:
    vetted: list[VettedTopic] = []
    for topic in canonical_topics:
        decision, allow_pairwise, reason = _topic_decision(topic)
        vetted.append(
            VettedTopic(
                canonical_topic_id=topic.canonical_topic_id,
                canonical_label=topic.label,
                decision=decision,
                allow_single_topic_questions=decision != "reject",
                allow_pairwise_questions=allow_pairwise,
                reason=reason,
                final_topic_type=topic.topic_type,
                evidence_spans=topic.evidence,
            )
        )
    return vetted


def _vet_pairs(
    related_pairs: list[RelatedTopicPair],
    vetted_topics: list[VettedTopic],
) -> list[VettedTopicPair]:
    by_label = {topic.canonical_label: topic for topic in vetted_topics}
    decisions: list[VettedTopicPair] = []
    for pair in related_pairs:
        left = by_label.get(pair.topic_x)
        right = by_label.get(pair.topic_y)
        keep_pair = (
            left is not None
            and right is not None
            and left.decision != "reject"
            and right.decision != "reject"
            and left.allow_pairwise_questions
            and right.allow_pairwise_questions
            and bool(pair.evidence_spans)
        )
        decisions.append(
            VettedTopicPair(
                pair_id=pair.pair_id,
                topic_x=pair.topic_x,
                topic_y=pair.topic_y,
                decision="keep_pair" if keep_pair else "reject_pair",
                reason=_pair_reason(pair, left, right, keep_pair),
                relation_type=pair.relation_type,
                evidence_spans=pair.evidence_spans,
            )
        )
    return decisions


def _topic_decision(topic: CanonicalTopic) -> tuple[str, bool, str]:
    if topic.topic_type in WRAPPER_TYPES or is_heading_like_topic(topic.label):
        return "reject", False, "wrapper_or_heading_like_topic"
    if topic.topic_type in {"metric", "test"}:
        return "keep", True, "strong_atomic_metric_or_test"
    if topic.topic_type in {"procedure", "tool", "method"}:
        return "keep", True, "strong_atomic_skill_topic"
    if topic.topic_type == "unknown":
        return "keep_entry_only", False, "weak_type_support_entry_only"
    return "keep", True, "strong_atomic_concept"


def _pair_reason(
    pair: RelatedTopicPair,
    left: VettedTopic | None,
    right: VettedTopic | None,
    keep_pair: bool,
) -> str:
    if keep_pair:
        return "paired_scope_supported"
    if not pair.evidence_spans:
        return "missing_relation_evidence"
    if left is None or right is None:
        return "missing_topic_decision"
    if left.decision == "reject" or right.decision == "reject":
        return "topic_rejected"
    if not left.allow_pairwise_questions or not right.allow_pairwise_questions:
        return "pairwise_blocked_by_topic_policy"
    return "invalid_pair"
