from __future__ import annotations

import re

from course_pipeline.schemas import (
    AnswerRecord,
    CanonicalTopic,
    GeneratedQuestion,
    QuestionValidationRecord,
    RelatedTopicPair,
    SemanticReviewDecision,
    SemanticReviewResult,
    SemanticStageResult,
    SyntheticAnswerRecord,
    SyntheticAnswerValidationRecord,
    Topic,
)


def apply_semantic_review(
    semantic_result: SemanticStageResult,
    review_result: SemanticReviewResult | None,
) -> SemanticStageResult:
    if review_result is None or not review_result.decisions:
        return semantic_result

    topics = list(semantic_result.topics)
    correlated_topics = list(semantic_result.correlated_topics)
    topic_questions = list(semantic_result.topic_questions)
    correlated_topic_questions = list(semantic_result.correlated_topic_questions)
    synthetic_answers = list(semantic_result.synthetic_answers)

    for decision in review_result.decisions:
        if decision.item_type == "topic":
            topics = _apply_topic_decision(topics, decision)
        elif decision.item_type == "correlated_topic":
            correlated_topics = _apply_correlated_decision(correlated_topics, decision)
        elif decision.item_type == "question":
            topic_questions = _apply_question_decision(topic_questions, decision)
            correlated_topic_questions = _apply_question_decision(
                correlated_topic_questions, decision
            )
        elif decision.item_type == "synthetic_answer":
            synthetic_answers = _apply_answer_decision(synthetic_answers, decision)

    return SemanticStageResult(
        topics=topics,
        correlated_topics=correlated_topics,
        topic_questions=topic_questions,
        correlated_topic_questions=correlated_topic_questions,
        synthetic_answers=synthetic_answers,
    )


def semantic_topics_to_canonical_topics(
    semantic_result: SemanticStageResult,
) -> list[CanonicalTopic]:
    topics: list[CanonicalTopic] = []
    for index, topic in enumerate(semantic_result.topics, start=1):
        aliases = list(dict.fromkeys([topic.label, *topic.aliases]))
        topics.append(
            CanonicalTopic(
                canonical_topic_id=f"ct_{index:03d}",
                label=topic.normalized_label,
                aliases=aliases,
                member_topic_ids=[f"semantic_topic_{index:03d}"],
                topic_type=_semantic_topic_type_to_legacy(topic.topic_type),
            )
        )
    return topics


def semantic_topics_to_topics(semantic_result: SemanticStageResult) -> list[Topic]:
    topics: list[Topic] = []
    for index, item in enumerate(semantic_result.topics, start=1):
        topics.append(
            Topic(
                topic_id=f"semantic_t_{index:03d}",
                label=item.normalized_label,
                topic_type=_semantic_topic_type_to_legacy(item.topic_type),
                description=item.rationale,
                confidence=item.confidence,
            )
        )
    return topics


def semantic_correlations_to_related_pairs(
    semantic_result: SemanticStageResult,
) -> list[RelatedTopicPair]:
    pairs: list[RelatedTopicPair] = []
    for index, item in enumerate(semantic_result.correlated_topics, start=1):
        if len(item.topics) < 2:
            continue
        pairs.append(
            RelatedTopicPair(
                pair_id=f"pair_{index:03d}",
                topic_x=item.topics[0],
                topic_y=item.topics[1],
                relation_type=item.relationship_type,
                confidence=item.strength,
            )
        )
    return pairs


def semantic_questions_to_generated_questions(
    semantic_result: SemanticStageResult,
) -> tuple[list[GeneratedQuestion], list[GeneratedQuestion]]:
    single_topic: list[GeneratedQuestion] = []
    correlated: list[GeneratedQuestion] = []

    for question in semantic_result.topic_questions:
        single_topic.append(
            GeneratedQuestion(
                question_id=question.question_id,
                relevant_topics=question.relevant_topics,
                source_refs=question.source_refs,
                family=question.question_family,
                pattern="semantic_stage",
                question_text=question.question_text,
                generation_scope="single_topic",
            )
        )

    for question in semantic_result.correlated_topic_questions:
        correlated.append(
            GeneratedQuestion(
                question_id=question.question_id,
                relevant_topics=question.relevant_topics,
                source_refs=question.source_refs,
                family=question.question_family,
                pattern="semantic_stage",
                question_text=question.question_text,
                generation_scope="pairwise",
            )
        )

    return single_topic, correlated


def generated_questions_to_validations(
    questions: list[GeneratedQuestion],
) -> list[QuestionValidationRecord]:
    return [
        QuestionValidationRecord(
            question_id=question.question_id,
            relevant_topics=question.relevant_topics,
            status="accepted",
            original_text=question.question_text,
            final_text=question.question_text,
            question_family=question.family,
            required_entry=question.required_entry,
            anchor_label=question.anchor_label,
        )
        for question in questions
    ]


def semantic_answers_to_records(
    *,
    run_id: str,
    course_id: str,
    model_name: str,
    semantic_result: SemanticStageResult,
    questions: list[GeneratedQuestion],
) -> tuple[list[SyntheticAnswerRecord], list[SyntheticAnswerValidationRecord], list[AnswerRecord]]:
    question_by_text = {question.question_text: question for question in questions}
    synthetic_answers: list[SyntheticAnswerRecord] = []
    validations: list[SyntheticAnswerValidationRecord] = []
    answers: list[AnswerRecord] = []

    for answer_index, semantic_answer in enumerate(semantic_result.synthetic_answers, start=1):
        question = question_by_text.get(semantic_answer.question_text)
        if question is None:
            continue
        canonical_topic = (
            question.relevant_topics[0] if question.relevant_topics else f"topic_{answer_index:03d}"
        )
        synthetic_record = SyntheticAnswerRecord(
            run_id=run_id,
            course_id=course_id,
            question_id=question.question_id,
            question_text=question.question_text,
            canonical_topic=canonical_topic,
            question_family=question.family,
            difficulty_band=semantic_answer.difficulty_band,
            answer_text=semantic_answer.answer_text,
            target_verbosity="brief",
            model_name=model_name,
            prompt_family="semantic_stage",
            confidence=semantic_answer.confidence,
            risks=[],
        )
        validation_record = SyntheticAnswerValidationRecord(
            run_id=run_id,
            course_id=course_id,
            question_id=question.question_id,
            original_answer_text=semantic_answer.answer_text,
            decision="accept",
            correctness=semantic_answer.confidence,
            sufficiency=semantic_answer.confidence,
            brevity=semantic_answer.confidence,
            pedagogical_fit=semantic_answer.confidence,
            difficulty_alignment=semantic_answer.confidence,
            clarity=semantic_answer.confidence,
            contradiction_risk=0.0,
            scope_drift=0.0,
        )
        answer_record = AnswerRecord(
            question_id=question.question_id,
            question_text=question.question_text,
            answer_text=semantic_answer.answer_text,
            correctness="correct",
            confidence=semantic_answer.confidence,
            answer_mode="synthetic_tutor_answer",
            validation_status="accept",
            provenance={
                "topic_labels": question.relevant_topics,
                "synthetic_model_name": model_name,
                "prompt_family": "semantic_stage",
            },
            source_refs=question.source_refs,
        )
        synthetic_answers.append(synthetic_record)
        validations.append(validation_record)
        answers.append(answer_record)

    return synthetic_answers, validations, answers


def _apply_topic_decision(topics: list, decision: SemanticReviewDecision) -> list:
    updated: list = []
    for topic in topics:
        if topic.normalized_label != decision.target_id:
            updated.append(topic)
            continue
        if decision.decision == "reject":
            continue
        if decision.decision == "rewrite" and decision.rewritten_payload:
            updated.append(
                type(topic).model_validate(
                    {
                        **topic.model_dump(),
                        **_normalize_topic_rewrite_payload(decision.rewritten_payload),
                    }
                )
            )
            continue
        if decision.decision == "merge" and decision.merged_into:
            continue
        updated.append(topic)
    return updated


def _apply_correlated_decision(items: list, decision: SemanticReviewDecision) -> list:
    updated: list = []
    for item in items:
        item_id = "|".join(item.topics)
        if item_id != decision.target_id:
            updated.append(item)
            continue
        if decision.decision == "reject":
            continue
        if decision.decision == "rewrite" and decision.rewritten_payload:
            updated.append(
                type(item).model_validate(
                    {
                        **item.model_dump(),
                        **_normalize_correlated_rewrite_payload(decision.rewritten_payload),
                    }
                )
            )
            continue
        if decision.decision == "merge" and decision.merged_into:
            continue
        updated.append(item)
    return updated


def _apply_question_decision(items: list, decision: SemanticReviewDecision) -> list:
    updated: list = []
    for item in items:
        if item.question_id != decision.target_id:
            updated.append(item)
            continue
        if decision.decision == "reject" and _is_hard_reject_rationale(decision.rationale):
            continue
        if decision.decision == "rewrite" and decision.rewritten_payload:
            updated.append(
                type(item).model_validate(
                    {
                        **item.model_dump(),
                        **_normalize_question_rewrite_payload(decision.rewritten_payload),
                    }
                )
            )
            continue
        if decision.decision == "merge" and decision.merged_into:
            continue
        updated.append(item)
    return updated


def _apply_answer_decision(items: list, decision: SemanticReviewDecision) -> list:
    updated: list = []
    for item in items:
        if item.question_text != decision.target_id:
            updated.append(item)
            continue
        if decision.decision == "reject" and _is_hard_reject_rationale(decision.rationale):
            continue
        if decision.decision == "rewrite" and decision.rewritten_payload:
            updated.append(
                type(item).model_validate(
                    {
                        **item.model_dump(),
                        **_normalize_answer_rewrite_payload(decision.rewritten_payload),
                    }
                )
            )
            continue
        if decision.decision == "merge" and decision.merged_into:
            continue
        updated.append(item)
    return updated


def _semantic_topic_type_to_legacy(topic_type: str) -> str:
    if topic_type in {"concept", "procedure", "tool", "metric", "test"}:
        return topic_type
    if topic_type == "diagnostic":
        return "other"
    if topic_type == "comparison_axis":
        return "comparison_pair_candidate"
    if topic_type == "decision_point":
        return "other"
    return "concept"


def _normalize_topic_rewrite_payload(payload: dict) -> dict:
    row = dict(payload)
    if "topic_type" in row:
        row["topic_type"] = _normalize_topic_type(row.get("topic_type"))
    row.setdefault("aliases", payload.get("aliases", []))
    row.setdefault("source_refs", payload.get("source_refs", []))
    if not row.get("rationale"):
        row["rationale"] = "normalized_from_semantic_review_rewrite"
    return row


def _normalize_correlated_rewrite_payload(payload: dict) -> dict:
    row = dict(payload)
    if "relationship_type" in row:
        row["relationship_type"] = _normalize_relationship_type(
            row.get("relationship_type")
        )
    if not row.get("rationale"):
        row["rationale"] = "normalized_from_semantic_review_rewrite"
    return row


def _normalize_question_rewrite_payload(payload: dict) -> dict:
    row = dict(payload)
    question_text = str(row.get("question_text") or "").strip()
    if "question_family" in row:
        row["question_family"] = _normalize_question_family(row.get("question_family"))
    elif question_text:
        row["question_family"] = _infer_question_family(
            question_text,
            scope=row.get("question_scope", "single_topic"),
        )
    if "question_scope" in row:
        row["question_scope"] = (
            "correlated_topics"
            if str(row.get("question_scope")).strip().lower() in {"correlated_topics", "pairwise"}
            else "single_topic"
        )
    if "topics" in row and "relevant_topics" not in row:
        topics = row.get("topics") or []
        row["relevant_topics"] = [topics] if isinstance(topics, str) else list(topics)
    if not row.get("rationale"):
        row["rationale"] = "normalized_from_semantic_review_rewrite"
    row.setdefault("source_refs", payload.get("source_refs", []))
    return row


def _normalize_answer_rewrite_payload(payload: dict) -> dict:
    row = dict(payload)
    if "answer_mode" in row:
        row["answer_mode"] = "synthetic_tutor_answer"
    return row


def _is_hard_reject_rationale(rationale: str | None) -> bool:
    normalized = str(rationale or "").strip().lower()
    if not normalized:
        return False
    hard_reject_markers = (
        "incorrect",
        "wrong",
        "contradict",
        "conflict",
        "mismatch",
        "off-topic",
        "off topic",
        "malformed",
        "unintelligible",
        "unsafe",
        "empty",
        "unusable",
        "duplicate",
    )
    return any(marker in normalized for marker in hard_reject_markers)


def _normalize_question_family(value: object) -> str:
    normalized = re.sub(r"[\s\-]+", "_", str(value or "").strip().lower())
    mapping = {
        "what_is": "what_is",
        "why_is": "why_is",
        "when_to_use": "when_to_use",
        "how_does_it_work": "how_does_it_work",
        "what_is_it_used_for": "what_is_it_used_for",
        "how_are_x_and_y_related": "how_are_x_and_y_related",
        "what_is_the_difference_between_x_and_y": "what_is_the_difference_between_x_and_y",
        "why_are_x_and_y_often_used_together": "why_are_x_and_y_often_used_together",
        "when_would_you_use_x_instead_of_y": "when_would_you_use_x_instead_of_y",
        "how_is_it_used": "what_is_it_used_for",
        "what_is_it_for": "what_is_it_used_for",
        "difference_between": "what_is_the_difference_between_x_and_y",
        "used_together": "why_are_x_and_y_often_used_together",
    }
    return mapping.get(normalized, "what_is")


def _infer_question_family(question_text: str, *, scope: str) -> str:
    normalized = re.sub(r"\s+", " ", question_text.strip().lower())
    if scope == "correlated_topics":
        if normalized.startswith("how are "):
            return "how_are_x_and_y_related"
        if normalized.startswith("what is the difference between "):
            return "what_is_the_difference_between_x_and_y"
        if normalized.startswith("why are ") and "used together" in normalized:
            return "why_are_x_and_y_often_used_together"
        if normalized.startswith("when would you use ") and " instead of " in normalized:
            return "when_would_you_use_x_instead_of_y"
        return "how_are_x_and_y_related"
    if normalized.startswith("what is ") and " used for" in normalized:
        return "what_is_it_used_for"
    if normalized.startswith("what is "):
        return "what_is"
    if normalized.startswith("why is "):
        return "why_is"
    if normalized.startswith("when would you use ") or normalized.startswith("when should you use "):
        return "when_to_use"
    if normalized.startswith("how does ") or normalized.startswith("how do "):
        return "how_does_it_work"
    return "what_is"


def _normalize_relationship_type(value: object) -> str:
    normalized = re.sub(r"[\s\-]+", "_", str(value or "").strip().lower())
    if normalized in {
        "paired_scope",
        "prerequisite_adjacent",
        "commonly_confused",
        "comparison_worthy",
        "used_together",
        "evaluation_related",
    }:
        return normalized
    if normalized in {"procedure_on_concept", "foundation", "foundational_skills"}:
        return "prerequisite_adjacent"
    if normalized in {"related_data_structures"}:
        return "paired_scope"
    if normalized in {"comparison", "compare", "contrast"}:
        return "comparison_worthy"
    if normalized in {"related", "relationship", "connected"}:
        return "used_together"
    return "used_together"


def _normalize_topic_type(value: object) -> str:
    normalized = re.sub(r"[\s\-]+", "_", str(value or "").strip().lower())
    if normalized in {
        "concept",
        "procedure",
        "tool",
        "metric",
        "diagnostic",
        "test",
        "comparison_axis",
        "decision_point",
    }:
        return normalized
    if normalized in {"model", "framework", "pattern", "principle", "structure"}:
        return "concept"
    if normalized in {"library", "package", "function", "operator", "keyword"}:
        return "tool"
    if normalized in {"workflow", "technique", "method", "process"}:
        return "procedure"
    if normalized in {"comparison", "comparison_axis_candidate"}:
        return "comparison_axis"
    if normalized in {"decision", "choice"}:
        return "decision_point"
    return "concept"
