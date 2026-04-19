
from __future__ import annotations

import re
from course_pipeline.schemas import CanonicalTopic, Topic


def _norm(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\bthe\b\s+", "", text)
    text = re.sub(r"\bmodels\b$", "model", text)
    text = re.sub(r"\s+", " ", text)
    return text


def canonicalize_topics(topics: list[Topic]) -> list[CanonicalTopic]:
    groups: dict[str, list[Topic]] = {}
    for topic in topics:
        groups.setdefault(_norm(topic.label), []).append(topic)

    canonical: list[CanonicalTopic] = []
    for idx, (norm_label, members) in enumerate(groups.items(), start=1):
        canonical.append(
            CanonicalTopic(
                canonical_topic_id=f"ct_{idx:03d}",
                label=norm_label,
                aliases=sorted({m.label for m in members}),
                member_topic_ids=[m.topic_id for m in members],
                topic_type=members[0].topic_type,
                evidence=_merged_evidence(members),
            )
        )
    return canonical


def _merged_evidence(topics: list[Topic]) -> list:
    seen: set[tuple[str, str]] = set()
    merged = []
    for topic in topics:
        for evidence in topic.evidence:
            key = (evidence.source, evidence.text)
            if key in seen:
                continue
            seen.add(key)
            merged.append(evidence)
    return merged
