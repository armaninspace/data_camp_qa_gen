from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time

from course_pipeline.io_utils import read_jsonl, write_jsonl, write_yaml
from course_pipeline.llm import LLMClient
from course_pipeline.run_logging import RunLogger, StageTimer
from course_pipeline.schemas import (
    AnswerRecord,
    FineTuneRow,
    SyntheticAnswerRecord,
    SyntheticAnswerValidationRecord,
)


@dataclass
class SyntheticRunResult:
    synthetic_answers: list[SyntheticAnswerRecord]
    validations: list[SyntheticAnswerValidationRecord]
    rewrites: list[dict]
    fine_tune_rows: list[FineTuneRow]


def synthesize_answers_for_course(
    *,
    run_id: str,
    course: dict,
    canonical_topics: list[dict],
    validations: list[dict],
    related_pairs: list[dict],
    synth_client: LLMClient,
    validate_client: LLMClient,
    logger: RunLogger | None = None,
) -> SyntheticRunResult:
    topic_by_course_and_label = {
        (str(row["course_id"]), str(row["label"])): row for row in canonical_topics
    }

    pair_by_course_and_topics = {
        (
            str(row["course_id"]),
            tuple(sorted((str(row["topic_x"]), str(row["topic_y"])))),
        ): row
        for row in related_pairs
    }

    synthetic_answers: list[SyntheticAnswerRecord] = []
    validation_records: list[SyntheticAnswerValidationRecord] = []
    rewrites: list[dict] = []
    family_counts: dict[str, int] = {}

    course_id = str(course["course_id"])
    for validation in validations:
        if validation.get("status") == "rejected":
            continue

        relevant_topics = [str(item) for item in validation.get("relevant_topics", [])]
        canonical_topic = relevant_topics[0] if relevant_topics else "unknown"
        topic_row = topic_by_course_and_label.get((course_id, canonical_topic), {})
        pair_context = None
        if len(relevant_topics) == 2:
            pair_context = pair_by_course_and_topics.get(
                (course_id, tuple(sorted(relevant_topics)))
            )

        payload = _synthesis_payload(
            run_id=run_id,
            course=course,
            validation=validation,
            topic_row=topic_row,
            pair_context=pair_context,
        )
        synth_prompt = _render_prompt(
            Path(__file__).resolve().parents[1] / "prompts" / "synthesize_answers.md",
            payload,
        )
        synth_started = time.perf_counter()
        synth_json = synth_client.complete_json(synth_prompt, "synthetic_answer")
        if logger is not None:
            logger.log_llm_call(
                course_id=course_id,
                stage="synthesize_answers",
                prompt_family="synthesize_answer",
                configured_model=synth_client.model,
                requested_model=synth_client.model,
                actual_model=synth_client.model,
                actual_model_source="configured_model",
                provider_request_id=None,
                latency_ms=int((time.perf_counter() - synth_started) * 1000),
                tokens_in=None,
                tokens_out=None,
                retry_count=0,
                status="success",
            )
        synth_record = SyntheticAnswerRecord(
            run_id=run_id,
            course_id=course_id,
            question_id=str(validation["question_id"]),
            question_text=str(validation["final_text"] or validation["original_text"]),
            canonical_topic=canonical_topic,
            question_family=str(validation.get("question_family", "entry")),
            difficulty_band=_difficulty_band(course),
            answer_text=str(synth_json["answer_text"]).strip(),
            target_verbosity=str(synth_json.get("target_verbosity", "brief")),
            model_name=synth_client.model,
            prompt_family="synthesize_answer",
            confidence=_safe_float(synth_json.get("self_assessed_confidence")),
            risks=[str(item) for item in synth_json.get("notable_risks", [])],
        )
        synthetic_answers.append(synth_record)

        validate_prompt = _render_prompt(
            Path(__file__).resolve().parents[1] / "prompts" / "validate_synth_answers.md",
            {
                **payload,
                "answer": synth_record.answer_text,
            },
        )
        validate_started = time.perf_counter()
        validate_json = validate_client.complete_json(
            validate_prompt,
            "validate_synthetic_answer",
        )
        if logger is not None:
            logger.log_llm_call(
                course_id=course_id,
                stage="synthesize_answers",
                prompt_family="validate_synthetic_answer",
                configured_model=validate_client.model,
                requested_model=validate_client.model,
                actual_model=validate_client.model,
                actual_model_source="configured_model",
                provider_request_id=None,
                latency_ms=int((time.perf_counter() - validate_started) * 1000),
                tokens_in=None,
                tokens_out=None,
                retry_count=0,
                status="success",
            )
        validation_record = SyntheticAnswerValidationRecord(
            run_id=run_id,
            course_id=course_id,
            question_id=synth_record.question_id,
            original_answer_text=synth_record.answer_text,
            decision=str(validate_json["decision"]),
            correctness=_safe_float(validate_json.get("correctness"), 0.0),
            sufficiency=_safe_float(validate_json.get("sufficiency"), 0.0),
            brevity=_safe_float(validate_json.get("brevity"), 0.0),
            pedagogical_fit=_safe_float(validate_json.get("pedagogical_fit"), 0.0),
            difficulty_alignment=_safe_float(validate_json.get("difficulty_alignment"), 0.0),
            clarity=_safe_float(validate_json.get("clarity"), 0.0),
            contradiction_risk=_safe_float(validate_json.get("contradiction_risk"), 0.0),
            scope_drift=_safe_float(validate_json.get("scope_drift"), 0.0),
            rewritten_answer_text=_optional_text(validate_json.get("rewritten_answer_text")),
            reject_reasons=[str(item) for item in validate_json.get("reject_reasons", [])],
        )
        validation_records.append(validation_record)

        if validation_record.decision == "rewrite" and validation_record.rewritten_answer_text:
            rewrites.append(
                {
                    "run_id": run_id,
                    "course_id": course_id,
                    "question_id": synth_record.question_id,
                    "original_answer_text": synth_record.answer_text,
                    "rewritten_answer_text": validation_record.rewritten_answer_text,
                }
            )
        family = synth_record.question_family
        family_counts[family] = family_counts.get(family, 0) + 1

    fine_tune_rows = build_fine_tune_rows(
        synthetic_answers=synthetic_answers,
        validations=validation_records,
    )
    return SyntheticRunResult(
        synthetic_answers=synthetic_answers,
        validations=validation_records,
        rewrites=rewrites,
        fine_tune_rows=fine_tune_rows,
    )


def run_synthetic_answering(
    *,
    run_dir: str | Path,
    output_dir: str | Path | None = None,
    synth_client: LLMClient,
    validate_client: LLMClient,
    logger: RunLogger | None = None,
) -> SyntheticRunResult:
    run_root = Path(run_dir)
    out_root = Path(output_dir) if output_dir is not None else run_root
    run_id = run_root.name

    normalized_courses = {
        str(row["course_id"]): row for row in read_jsonl(run_root / "normalized_courses.jsonl")
    }
    canonical_topics = read_jsonl(run_root / "canonical_topics.jsonl")
    validations = read_jsonl(run_root / "question_validation.jsonl")
    related_pairs = read_jsonl(run_root / "related_topic_pairs.jsonl")

    if logger is not None:
        stage_timer = StageTimer(
            logger,
            course_id="__run__",
            stage="run_synthetic_answering",
            input_row_count=len(validations),
        )
    else:
        stage_timer = None

    synthetic_answers = []
    validation_records = []
    rewrites = []
    family_counts: dict[str, int] = {}
    for course_id, course in normalized_courses.items():
        course_validations = [row for row in validations if str(row["course_id"]) == course_id]
        if not course_validations:
            continue
        course_result = synthesize_answers_for_course(
            run_id=run_id,
            course=course,
            canonical_topics=canonical_topics,
            validations=course_validations,
            related_pairs=related_pairs,
            synth_client=synth_client,
            validate_client=validate_client,
            logger=logger,
        )
        synthetic_answers.extend(course_result.synthetic_answers)
        validation_records.extend(course_result.validations)
        rewrites.extend(course_result.rewrites)
        for answer in course_result.synthetic_answers:
            family = answer.question_family
            family_counts[family] = family_counts.get(family, 0) + 1

    fine_tune_rows = build_fine_tune_rows(
        synthetic_answers=synthetic_answers,
        validations=validation_records,
    )

    write_jsonl(out_root / "synthetic_answers.jsonl", [item.model_dump() for item in synthetic_answers])
    write_jsonl(
        out_root / "synthetic_answer_validation.jsonl",
        [item.model_dump() for item in validation_records],
    )
    write_jsonl(out_root / "synthetic_answer_rewrites.jsonl", rewrites)
    write_jsonl(out_root / "fine_tune_rows.jsonl", [item.model_dump() for item in fine_tune_rows])
    write_jsonl(out_root / "ft_dataset.jsonl", [item.model_dump() for item in fine_tune_rows])
    write_yaml(
        out_root / "ft_run_summary.yaml",
        _ft_summary(
            fine_tune_rows,
            validation_records,
            synthetic_answers=synthetic_answers,
            family_counts=family_counts,
        ),
    )

    if stage_timer is not None:
        stage_timer.finish(output_row_count=len(fine_tune_rows))

    return SyntheticRunResult(
        synthetic_answers=synthetic_answers,
        validations=validation_records,
        rewrites=rewrites,
        fine_tune_rows=fine_tune_rows,
    )


def synthetic_results_to_answer_records(
    *,
    synthetic_answers: list[SyntheticAnswerRecord],
    validations: list[SyntheticAnswerValidationRecord],
    question_provenance: dict[str, dict] | None = None,
) -> list[AnswerRecord]:
    validation_by_question = {
        (item.course_id, item.question_id): item for item in validations
    }
    answers: list[AnswerRecord] = []
    question_provenance = question_provenance or {}
    for item in synthetic_answers:
        validation = validation_by_question.get((item.course_id, item.question_id))
        if validation is None or validation.decision == "reject":
            continue
        final_answer = (
            validation.rewritten_answer_text
            if validation.decision == "rewrite" and validation.rewritten_answer_text
            else item.answer_text
        )
        provenance = question_provenance.get(item.question_id, {})
        answers.append(
            AnswerRecord(
                question_id=item.question_id,
                question_text=item.question_text,
                answer_text=final_answer,
                correctness=_correctness_label(validation.correctness),
                confidence=validation.correctness,
                evidence=[],
                answer_mode="synthetic_tutor_answer",
                validation_status=validation.decision,
                rewrite_applied=validation.decision == "rewrite",
                provenance={
                    "topic_labels": provenance.get("topic_labels", []),
                    "source_refs": provenance.get("source_refs", []),
                    "synthetic_model_name": item.model_name,
                    "prompt_family": item.prompt_family,
                },
            )
        )
    return answers


def build_fine_tune_rows(
    *,
    synthetic_answers: list[SyntheticAnswerRecord],
    validations: list[SyntheticAnswerValidationRecord],
) -> list[FineTuneRow]:
    validation_by_question = {
        (item.course_id, item.question_id): item for item in validations
    }
    rows: list[FineTuneRow] = []
    for answer in synthetic_answers:
        validation = validation_by_question.get((answer.course_id, answer.question_id))
        if validation is None or validation.decision == "reject":
            continue

        final_answer = (
            validation.rewritten_answer_text
            if validation.decision == "rewrite" and validation.rewritten_answer_text
            else answer.answer_text
        )
        rows.append(
            FineTuneRow(
                run_id=answer.run_id,
                course_id=answer.course_id,
                question_id=answer.question_id,
                prompt=answer.question_text,
                completion=final_answer,
                question_text=answer.question_text,
                answer_text=final_answer,
                canonical_topic=answer.canonical_topic,
                question_family=answer.question_family,
                difficulty_band=answer.difficulty_band,
                answer_mode=answer.answer_mode,
                provenance={
                    "synthetic_model_name": answer.model_name,
                    "validation_decision": validation.decision,
                    "prompt_family": answer.prompt_family,
                },
                metadata={
                    "target_verbosity": answer.target_verbosity,
                    "risks": answer.risks,
                },
            )
        )
    return rows


def build_fine_tune_rows_from_artifacts(
    *,
    run_dir: str | Path,
    output_dir: str | Path | None = None,
) -> list[FineTuneRow]:
    run_root = Path(run_dir)
    out_root = Path(output_dir) if output_dir is not None else run_root
    synthetic_answers = [
        SyntheticAnswerRecord.model_validate(row)
        for row in read_jsonl(run_root / "synthetic_answers.jsonl")
    ]
    validations = [
        SyntheticAnswerValidationRecord.model_validate(row)
        for row in read_jsonl(run_root / "synthetic_answer_validation.jsonl")
    ]
    fine_tune_rows = build_fine_tune_rows(
        synthetic_answers=synthetic_answers,
        validations=validations,
    )
    write_jsonl(out_root / "fine_tune_rows.jsonl", [item.model_dump() for item in fine_tune_rows])
    write_jsonl(out_root / "ft_dataset.jsonl", [item.model_dump() for item in fine_tune_rows])
    family_counts: dict[str, int] = {}
    for answer in synthetic_answers:
        family = answer.question_family
        family_counts[family] = family_counts.get(family, 0) + 1
    write_yaml(
        out_root / "ft_run_summary.yaml",
        _ft_summary(
            fine_tune_rows,
            validations,
            synthetic_answers=synthetic_answers,
            family_counts=family_counts,
        ),
    )
    return fine_tune_rows


def render_ft_bundles(
    *,
    run_dir: str | Path,
    output_dir: str | Path | None = None,
) -> dict[str, dict]:
    run_root = Path(run_dir)
    out_root = Path(output_dir) if output_dir is not None else run_root
    normalized_courses = {
        str(row["course_id"]): row for row in read_jsonl(run_root / "normalized_courses.jsonl")
    }
    synthetic_answers = read_jsonl(run_root / "synthetic_answers.jsonl")
    validations = read_jsonl(run_root / "synthetic_answer_validation.jsonl")

    answers_by_course: dict[str, list[dict]] = {}
    for row in synthetic_answers:
        answers_by_course.setdefault(str(row["course_id"]), []).append(row)
    validations_by_question = {
        (str(row["course_id"]), str(row["question_id"])): row for row in validations
    }

    bundles: dict[str, dict] = {}
    for course_id, answers in answers_by_course.items():
        course = normalized_courses.get(course_id, {"course_id": course_id})
        questions: list[dict] = []
        accepted = 0
        rewritten = 0
        rejected = 0
        for answer in answers:
            validation = validations_by_question.get((course_id, str(answer["question_id"])), {})
            decision = validation.get("decision")
            if decision == "accept":
                accepted += 1
            elif decision == "rewrite":
                rewritten += 1
            elif decision == "reject":
                rejected += 1
            final_text = validation.get("rewritten_answer_text") or answer["answer_text"]
            questions.append(
                {
                    "question_id": answer["question_id"],
                    "question_text": answer["question_text"],
                    "canonical_topic": answer["canonical_topic"],
                    "question_family": answer["question_family"],
                    "difficulty_band": answer.get("difficulty_band"),
                    "synthetic_answer": {
                        "answer_text": final_text,
                        "decision": decision,
                        "answer_mode": answer["answer_mode"],
                        "scores": {
                            "correctness": validation.get("correctness"),
                            "brevity": validation.get("brevity"),
                            "pedagogical_fit": validation.get("pedagogical_fit"),
                        },
                    },
                }
            )
        bundle = {
            "course_id": course_id,
            "course_title": course.get("title"),
            "synthetic_answer_summary": {
                "accepted": accepted,
                "rewritten": rewritten,
                "rejected": rejected,
                "average_answer_length_words": round(
                    (
                        sum(
                            len(
                                (
                                    validations_by_question.get(
                                        (course_id, str(answer["question_id"])),
                                        {},
                                    ).get("rewritten_answer_text")
                                    or answer["answer_text"]
                                ).split()
                            )
                            for answer in answers
                        )
                        / len(answers)
                    ),
                    2,
                )
                if answers
                else 0.0,
            },
            "family_counts": _course_family_counts(answers),
            "questions": questions,
        }
        write_yaml(out_root / "ft_bundle" / f"{course_id}.yaml", bundle)
        bundles[course_id] = bundle
    return bundles


def _synthesis_payload(
    *,
    run_id: str,
    course: dict,
    validation: dict,
    topic_row: dict,
    pair_context: dict | None,
) -> dict[str, str]:
    return {
        "run_id": run_id,
        "question": str(validation.get("final_text") or validation.get("original_text") or ""),
        "question_family": str(validation.get("question_family", "entry")),
        "difficulty_band": _difficulty_band(course) or "unknown",
        "topic_label": str(topic_row.get("label", validation.get("relevant_topics", ["unknown"])[0])),
        "topic_type": str(topic_row.get("topic_type", "concept")),
        "course_title": str(course.get("title", "")),
        "domain_tags": ", ".join(str(item) for item in course.get("metadata", {}).get("subjects", [])),
        "related_topics": ", ".join(str(item) for item in validation.get("relevant_topics", [])),
        "pair_context": "" if pair_context is None else str(pair_context.get("relation_type", "")),
    }


def _render_prompt(path: Path, payload: dict[str, str]) -> str:
    template = path.read_text(encoding="utf-8")
    return template.format(**payload)


def _difficulty_band(course: dict) -> str | None:
    metadata = course.get("metadata", {})
    level = metadata.get("level")
    if level is None:
        return None
    return str(level).strip().lower() or None


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_float(value: object, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _correctness_label(score: float) -> str:
    if score >= 0.8:
        return "correct"
    if score <= 0.4:
        return "incorrect"
    return "uncertain"


def _ft_summary(
    fine_tune_rows: list[FineTuneRow],
    validations: list[SyntheticAnswerValidationRecord],
    *,
    synthetic_answers: list[SyntheticAnswerRecord],
    family_counts: dict[str, int],
) -> dict:
    decision_counts = {
        "accept": sum(item.decision == "accept" for item in validations),
        "rewrite": sum(item.decision == "rewrite" for item in validations),
        "reject": sum(item.decision == "reject" for item in validations),
    }
    answer_lengths_by_family: dict[str, list[int]] = {}
    answer_texts_by_course: dict[str, list[str]] = {}
    for row in fine_tune_rows:
        answer_lengths_by_family.setdefault(row.question_family, []).append(
            len(row.answer_text.split())
        )
        answer_texts_by_course.setdefault(row.course_id, []).append(row.answer_text.strip().lower())

    duplicate_answer_count = 0
    for answer_texts in answer_texts_by_course.values():
        duplicate_answer_count += len(answer_texts) - len(set(answer_texts))

    return {
        "synthetic_answer_count": len(synthetic_answers),
        "decision_counts": decision_counts,
        "accepted_count": decision_counts["accept"],
        "rewritten_count": decision_counts["rewrite"],
        "rejected_count": decision_counts["reject"],
        "ft_row_count": len(fine_tune_rows),
        "family_counts": family_counts,
        "average_answer_length_by_family": {
            family: round(sum(lengths) / len(lengths), 2)
            for family, lengths in sorted(answer_lengths_by_family.items())
        },
        "average_answer_length_words": round(
            (
                sum(len(item.answer_text.split()) for item in fine_tune_rows) / len(fine_tune_rows)
            ),
            2,
        )
        if fine_tune_rows
        else 0.0,
        "rewrite_rate": round(
            decision_counts["rewrite"] / len(validations),
            4,
        )
        if validations
        else 0.0,
        "duplicate_answer_count": duplicate_answer_count,
    }


def _course_family_counts(answers: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for answer in answers:
        family = str(answer.get("question_family", "unknown"))
        counts[family] = counts.get(family, 0) + 1
    return counts
