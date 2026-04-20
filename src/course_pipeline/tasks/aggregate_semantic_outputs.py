from __future__ import annotations

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
            updated.append(type(topic).model_validate({**topic.model_dump(), **decision.rewritten_payload}))
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
            updated.append(type(item).model_validate({**item.model_dump(), **decision.rewritten_payload}))
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
        if decision.decision == "reject":
            continue
        if decision.decision == "rewrite" and decision.rewritten_payload:
            updated.append(type(item).model_validate({**item.model_dump(), **decision.rewritten_payload}))
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
        if decision.decision == "reject":
            continue
        if decision.decision == "rewrite" and decision.rewritten_payload:
            updated.append(type(item).model_validate({**item.model_dump(), **decision.rewritten_payload}))
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
