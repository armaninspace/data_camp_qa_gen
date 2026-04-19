from __future__ import annotations

from course_pipeline.schemas import CanonicalTopic, RelatedTopicPair, TopicEvidence
from course_pipeline.tasks.canonicalize import canonicalize_topics
from course_pipeline.tasks.discover_related_pairs import discover_related_pairs
from course_pipeline.tasks.extract_topics import extract_atomic_topics_baseline
from course_pipeline.tasks.normalize import normalize_course_record
from course_pipeline.tasks.vet_topics import vet_topics_and_pairs


def test_valid_related_pair_is_discovered_from_shared_evidence() -> None:
    raw = {
        "course_id": "1",
        "title": "Example",
        "overview": "Category labels and strings are core topics in this course.",
        "syllabus": [
            {
                "title": "Categorical and Text Data",
                "summary": "Categorical data and text data both appear in messy source systems.",
            }
        ],
    }

    course = normalize_course_record(raw)
    topics = extract_atomic_topics_baseline(course)
    canonical_topics = canonicalize_topics(topics)
    related_pairs = discover_related_pairs(canonical_topics)

    assert any(
        {pair.topic_x, pair.topic_y} == {"categorical data", "text data"}
        and pair.evidence_spans
        for pair in related_pairs
    )


def test_wrapper_topic_is_rejected_during_vetting() -> None:
    canonical_topics = [
        CanonicalTopic(
            canonical_topic_id="ct_1",
            label="case study",
            aliases=["Case Study"],
            member_topic_ids=["t1"],
            topic_type="case_study_container",
            evidence=[TopicEvidence(source="chapter_title", text="Case Study")],
        )
    ]

    vetted_topics, vetted_pairs = vet_topics_and_pairs(canonical_topics, [])

    assert vetted_topics[0].decision == "reject"
    assert vetted_topics[0].allow_single_topic_questions is False
    assert vetted_pairs == []


def test_invalid_related_pair_is_blocked_when_one_topic_is_rejected() -> None:
    canonical_topics = [
        CanonicalTopic(
            canonical_topic_id="ct_1",
            label="correlation",
            aliases=["correlation"],
            member_topic_ids=["t1"],
            topic_type="metric",
            evidence=[TopicEvidence(source="overview", text="Correlation compares series.")],
        ),
        CanonicalTopic(
            canonical_topic_id="ct_2",
            label="case study",
            aliases=["case study"],
            member_topic_ids=["t2"],
            topic_type="case_study_container",
            evidence=[TopicEvidence(source="chapter_title", text="Case Study")],
        ),
    ]
    related_pairs = [
        RelatedTopicPair(
            pair_id="p_001",
            topic_x="correlation",
            topic_y="case study",
            relation_type="shared_local_evidence",
            evidence_spans=[
                TopicEvidence(source="overview", text="Correlation appears before the case study.")
            ],
            confidence=0.6,
        )
    ]

    _, vetted_pairs = vet_topics_and_pairs(canonical_topics, related_pairs)

    assert vetted_pairs[0].decision == "reject_pair"
    assert vetted_pairs[0].reason == "topic_rejected"
