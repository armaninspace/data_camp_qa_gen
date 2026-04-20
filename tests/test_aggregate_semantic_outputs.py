from __future__ import annotations

from course_pipeline.schemas import SemanticReviewResult, SemanticStageResult
from course_pipeline.tasks.aggregate_semantic_outputs import (
    apply_semantic_review,
    generated_questions_to_validations,
    semantic_answers_to_records,
    semantic_questions_to_generated_questions,
    semantic_topics_to_canonical_topics,
)


def _semantic_result() -> SemanticStageResult:
    return SemanticStageResult.model_validate(
        {
            "topics": [
                {
                    "label": "Pandas",
                    "normalized_label": "pandas",
                    "topic_type": "tool",
                    "confidence": 0.95,
                    "course_centrality": 0.92,
                    "source_refs": ["overview"],
                    "rationale": "Central tool.",
                },
                {
                    "label": "Getting Started in Python",
                    "normalized_label": "getting started in python",
                    "topic_type": "concept",
                    "confidence": 0.4,
                    "course_centrality": 0.1,
                    "source_refs": ["chapter:1"],
                    "rationale": "Wrapper title.",
                },
            ],
            "correlated_topics": [],
            "topic_questions": [
                {
                    "question_id": "sq_001",
                    "question_text": "What is pandas?",
                    "question_family": "what_is",
                    "relevant_topics": ["pandas"],
                    "question_scope": "single_topic",
                    "rationale": "Natural entry question.",
                }
            ],
            "correlated_topic_questions": [],
            "synthetic_answers": [
                {
                    "question_text": "What is pandas?",
                    "answer_text": "Pandas is a Python library for tabular data.",
                    "answer_mode": "synthetic_tutor_answer",
                    "difficulty_band": "beginner",
                    "confidence": 0.96,
                    "answer_rationale": "Brief answer.",
                }
            ],
        }
    )


def test_apply_semantic_review_can_reject_topic() -> None:
    review = SemanticReviewResult.model_validate(
        {
            "decisions": [
                {
                    "item_type": "topic",
                    "target_id": "getting started in python",
                    "decision": "reject",
                    "rewritten_payload": {},
                    "merged_into": None,
                    "rationale": "Wrapper topic.",
                }
            ]
        }
    )

    result = apply_semantic_review(_semantic_result(), review)

    labels = [item.normalized_label for item in result.topics]
    assert labels == ["pandas"]


def test_semantic_bundle_transforms_to_legacy_structural_shapes() -> None:
    semantic_result = _semantic_result()

    canonical_topics = semantic_topics_to_canonical_topics(semantic_result)
    single_topic_questions, pairwise_questions = semantic_questions_to_generated_questions(
        semantic_result
    )
    validations = generated_questions_to_validations(single_topic_questions + pairwise_questions)
    synthetic_answers, synthetic_validations, answers = semantic_answers_to_records(
        run_id="run",
        course_id="24372",
        model_name="gpt-5.4",
        semantic_result=semantic_result,
        questions=single_topic_questions + pairwise_questions,
    )

    assert canonical_topics[0].label == "pandas"
    assert single_topic_questions[0].question_text == "What is pandas?"
    assert validations[0].status == "accepted"
    assert synthetic_answers[0].question_id == "sq_001"
    assert synthetic_validations[0].decision == "accept"
    assert answers[0].answer_mode == "synthetic_tutor_answer"
