from __future__ import annotations

from pathlib import Path

from course_pipeline.run_logging import RunLogger
from course_pipeline.tasks.synthesize_answers import (
    build_fine_tune_rows_from_artifacts,
    render_ft_bundles,
    run_synthetic_answering,
    synthetic_results_to_answer_records,
    synthesize_answers_for_course,
)
from course_pipeline.io_utils import read_jsonl, read_yaml, write_jsonl
from course_pipeline.schemas import SyntheticAnswerRecord, SyntheticAnswerValidationRecord


class FakeJsonClient:
    def __init__(self, model: str, responses: list[dict]) -> None:
        self.model = model
        self._responses = list(responses)
        self.prompts: list[tuple[str, str]] = []

    def complete_json(self, prompt: str, schema_name: str) -> dict:
        self.prompts.append((schema_name, prompt))
        if not self._responses:
            raise AssertionError(f"no fake response left for schema={schema_name}")
        return self._responses.pop(0)


def _write_synthetic_run_fixture(run_dir: Path) -> None:
    write_jsonl(
        run_dir / "normalized_courses.jsonl",
        [
            {
                "course_id": "24372",
                "title": "Time Series Analysis in Python",
                "metadata": {
                    "level": "beginner",
                    "subjects": ["python", "time series"],
                },
            },
            {
                "course_id": "24373",
                "title": "SQL Joins",
                "metadata": {
                    "level": "intermediate",
                    "subjects": ["sql"],
                },
            },
        ],
    )
    write_jsonl(
        run_dir / "canonical_topics.jsonl",
        [
            {
                "course_id": "24372",
                "canonical_topic_id": "ct_arima",
                "label": "ARIMA",
                "topic_type": "concept",
            },
            {
                "course_id": "24373",
                "canonical_topic_id": "ct_join",
                "label": "join",
                "topic_type": "procedure",
            },
        ],
    )
    write_jsonl(run_dir / "related_topic_pairs.jsonl", [])
    write_jsonl(
        run_dir / "question_validation.jsonl",
        [
            {
                "course_id": "24372",
                "question_id": "q_accept",
                "status": "accepted",
                "original_text": "What is ARIMA?",
                "final_text": "What is ARIMA?",
                "question_family": "entry",
                "relevant_topics": ["ARIMA"],
                "evidence_spans": [],
            },
            {
                "course_id": "24372",
                "question_id": "q_rewrite",
                "status": "accepted",
                "original_text": "When would you use ARIMA?",
                "final_text": "When would you use ARIMA?",
                "question_family": "procedure",
                "relevant_topics": ["ARIMA"],
                "evidence_spans": [],
            },
            {
                "course_id": "24373",
                "question_id": "q_reject",
                "status": "accepted",
                "original_text": "What is a join?",
                "final_text": "What is a join?",
                "question_family": "entry",
                "relevant_topics": ["join"],
                "evidence_spans": [],
            },
            {
                "course_id": "24373",
                "question_id": "q_skip",
                "status": "rejected",
                "original_text": "Bad question?",
                "final_text": None,
                "question_family": "entry",
                "relevant_topics": ["join"],
                "evidence_spans": [],
            },
        ],
    )


def test_synthetic_answer_path_generates_answers_without_brochure_evidence(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    _write_synthetic_run_fixture(run_dir)
    logger = RunLogger(run_id="run", root_dir=run_dir)
    logger.ensure_files()

    synth_client = FakeJsonClient(
        "gpt-5.4",
        [
            {
                "answer_text": "ARIMA models a time series using autoregression, differencing, and moving averages.",
                "answer_mode": "synthetic_tutor_answer",
                "target_verbosity": "brief",
                "self_assessed_confidence": 0.92,
                "notable_risks": [],
            },
            {
                "answer_text": "Use ARIMA when a series has structure over time and you want a forecasting model that can handle trend after differencing.",
                "answer_mode": "synthetic_tutor_answer",
                "target_verbosity": "brief",
                "self_assessed_confidence": 0.88,
                "notable_risks": ["may need seasonal variant"],
            },
            {
                "answer_text": "A join combines rows from tables using a related key.",
                "answer_mode": "synthetic_tutor_answer",
                "target_verbosity": "brief",
                "self_assessed_confidence": 0.9,
                "notable_risks": [],
            },
        ],
    )
    validate_client = FakeJsonClient(
        "gpt-5.4",
        [
            {
                "decision": "accept",
                "correctness": 0.98,
                "sufficiency": 0.95,
                "brevity": 0.94,
                "pedagogical_fit": 0.95,
                "difficulty_alignment": 0.96,
                "clarity": 0.97,
                "contradiction_risk": 0.01,
                "scope_drift": 0.01,
                "rewritten_answer_text": None,
                "reject_reasons": [],
            },
            {
                "decision": "rewrite",
                "correctness": 0.94,
                "sufficiency": 0.89,
                "brevity": 0.61,
                "pedagogical_fit": 0.9,
                "difficulty_alignment": 0.91,
                "clarity": 0.88,
                "contradiction_risk": 0.02,
                "scope_drift": 0.02,
                "rewritten_answer_text": "Use ARIMA when past values and forecast errors help explain the series after differencing removes trend.",
                "reject_reasons": [],
            },
            {
                "decision": "reject",
                "correctness": 0.2,
                "sufficiency": 0.4,
                "brevity": 0.7,
                "pedagogical_fit": 0.3,
                "difficulty_alignment": 0.3,
                "clarity": 0.5,
                "contradiction_risk": 0.8,
                "scope_drift": 0.4,
                "rewritten_answer_text": None,
                "reject_reasons": ["too_generic"],
            },
        ],
    )

    result = run_synthetic_answering(
        run_dir=run_dir,
        synth_client=synth_client,
        validate_client=validate_client,
        logger=logger,
    )

    assert len(result.synthetic_answers) == 3
    assert len(result.validations) == 3
    assert len(result.rewrites) == 1
    assert len(result.fine_tune_rows) == 2
    assert result.synthetic_answers[0].answer_mode == "synthetic_tutor_answer"
    assert "Answer: ARIMA" not in synth_client.prompts[0][1]
    assert "Answer:" in validate_client.prompts[0][1]
    assert "What is ARIMA?" in validate_client.prompts[0][1]

    persisted_answers = read_jsonl(run_dir / "synthetic_answers.jsonl")
    persisted_validations = read_jsonl(run_dir / "synthetic_answer_validation.jsonl")
    persisted_rewrites = read_jsonl(run_dir / "synthetic_answer_rewrites.jsonl")
    ft_rows = read_jsonl(run_dir / "ft_dataset.jsonl")
    summary = read_yaml(run_dir / "ft_run_summary.yaml")

    assert len(persisted_answers) == 3
    assert len(persisted_validations) == 3
    assert persisted_rewrites == [
        {
            "run_id": "run",
            "course_id": "24372",
            "question_id": "q_rewrite",
            "original_answer_text": "Use ARIMA when a series has structure over time and you want a forecasting model that can handle trend after differencing.",
            "rewritten_answer_text": "Use ARIMA when past values and forecast errors help explain the series after differencing removes trend.",
        }
    ]
    assert [row["question_id"] for row in ft_rows] == ["q_accept", "q_rewrite"]
    assert ft_rows[1]["completion"] == (
        "Use ARIMA when past values and forecast errors help explain the series after differencing removes trend."
    )
    assert summary["decision_counts"] == {"accept": 1, "rewrite": 1, "reject": 1}
    assert summary["ft_row_count"] == 2
    assert summary["family_counts"] == {"entry": 2, "procedure": 1}
    assert "duplicate_answer_count" in summary

    llm_logs = read_jsonl(run_dir / "logs" / "llm_calls.jsonl")
    assert len(llm_logs) == 6
    assert llm_logs[0]["prompt_family"] == "synthesize_answer"
    assert llm_logs[1]["prompt_family"] == "validate_synthetic_answer"


def test_build_ft_dataset_and_render_ft_bundle_use_final_rewritten_answers(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    _write_synthetic_run_fixture(run_dir)
    write_jsonl(
        run_dir / "synthetic_answers.jsonl",
        [
            {
                "run_id": "run",
                "course_id": "24372",
                "question_id": "q_accept",
                "question_text": "What is ARIMA?",
                "canonical_topic": "ARIMA",
                "question_family": "entry",
                "difficulty_band": "beginner",
                "answer_mode": "synthetic_tutor_answer",
                "answer_text": "ARIMA is a forecasting model.",
                "target_verbosity": "brief",
                "model_name": "gpt-5.4",
                "prompt_family": "synthesize_answer",
                "confidence": 0.9,
                "risks": [],
            },
            {
                "run_id": "run",
                "course_id": "24372",
                "question_id": "q_rewrite",
                "question_text": "When would you use ARIMA?",
                "canonical_topic": "ARIMA",
                "question_family": "procedure",
                "difficulty_band": "beginner",
                "answer_mode": "synthetic_tutor_answer",
                "answer_text": "Original long answer.",
                "target_verbosity": "brief",
                "model_name": "gpt-5.4",
                "prompt_family": "synthesize_answer",
                "confidence": 0.8,
                "risks": [],
            },
        ],
    )
    write_jsonl(
        run_dir / "synthetic_answer_validation.jsonl",
        [
            {
                "run_id": "run",
                "course_id": "24372",
                "question_id": "q_accept",
                "original_answer_text": "ARIMA is a forecasting model.",
                "decision": "accept",
                "correctness": 0.97,
                "sufficiency": 0.95,
                "brevity": 0.95,
                "pedagogical_fit": 0.95,
                "difficulty_alignment": 0.95,
                "clarity": 0.95,
                "contradiction_risk": 0.01,
                "scope_drift": 0.01,
                "rewritten_answer_text": None,
                "reject_reasons": [],
            },
            {
                "run_id": "run",
                "course_id": "24372",
                "question_id": "q_rewrite",
                "original_answer_text": "Original long answer.",
                "decision": "rewrite",
                "correctness": 0.9,
                "sufficiency": 0.88,
                "brevity": 0.6,
                "pedagogical_fit": 0.9,
                "difficulty_alignment": 0.9,
                "clarity": 0.85,
                "contradiction_risk": 0.02,
                "scope_drift": 0.02,
                "rewritten_answer_text": "Short rewritten answer.",
                "reject_reasons": [],
            },
        ],
    )

    rows = build_fine_tune_rows_from_artifacts(run_dir=run_dir)
    bundles = render_ft_bundles(run_dir=run_dir)

    assert len(rows) == 2
    assert rows[1].completion == "Short rewritten answer."
    assert bundles["24372"]["synthetic_answer_summary"]["rewritten"] == 1
    assert bundles["24372"]["family_counts"] == {"entry": 1, "procedure": 1}

    bundle_yaml = read_yaml(run_dir / "ft_bundle" / "24372.yaml")
    assert bundle_yaml["questions"][1]["synthetic_answer"]["answer_text"] == "Short rewritten answer."
    assert bundle_yaml["synthetic_answer_summary"]["average_answer_length_words"] > 0

def test_synthetic_results_to_answer_records_uses_rewrites_and_provenance() -> None:
    result = synthetic_results_to_answer_records(
        synthetic_answers=[
            SyntheticAnswerRecord(
                run_id="run",
                course_id="24372",
                question_id="q1",
                question_text="What is ARIMA?",
                canonical_topic="ARIMA",
                question_family="entry",
                difficulty_band="beginner",
                answer_text="Original answer.",
                target_verbosity="brief",
                model_name="gpt-5.4",
                prompt_family="synthesize_answer",
                confidence=0.9,
                risks=[],
            )
        ],
        validations=[
            SyntheticAnswerValidationRecord(
                run_id="run",
                course_id="24372",
                question_id="q1",
                original_answer_text="Original answer.",
                decision="rewrite",
                correctness=0.93,
                sufficiency=0.9,
                brevity=0.9,
                pedagogical_fit=0.9,
                difficulty_alignment=0.9,
                clarity=0.9,
                contradiction_risk=0.02,
                scope_drift=0.02,
                rewritten_answer_text="Rewritten answer.",
                reject_reasons=[],
            )
        ],
        question_provenance={
            "q1": {
                "topic_labels": ["ARIMA"],
                "source_refs": ["syllabus"],
                "evidence_spans": [{"source": "syllabus", "text": "ARIMA"}],
            }
        },
    )

    assert len(result) == 1
    assert result[0].answer_mode == "synthetic_tutor_answer"
    assert result[0].rewrite_applied is True
    assert result[0].validation_status == "rewrite"
    assert result[0].answer_text == "Rewritten answer."
    assert result[0].evidence[0].source == "syllabus"


def test_validator_scores_are_normalized_from_five_point_scale(tmp_path: Path) -> None:
    logger = RunLogger(run_id="run", root_dir=tmp_path / "run")
    logger.ensure_files()
    synth_client = FakeJsonClient(
        "gpt-5.4",
        [
            {
                "answer_text": "ARIMA is a forecasting model.",
                "target_verbosity": "brief",
                "self_assessed_confidence": 0.9,
                "notable_risks": [],
            }
        ],
    )
    validate_client = FakeJsonClient(
        "gpt-5.4",
        [
            {
                "decision": "accept",
                "correctness": 5.0,
                "sufficiency": 4.0,
                "brevity": 4.0,
                "pedagogical_fit": 5.0,
                "difficulty_alignment": 5.0,
                "clarity": 4.0,
                "contradiction_risk": 1.0,
                "scope_drift": 1.0,
                "rewritten_answer_text": None,
                "reject_reasons": [],
            }
        ],
    )

    result = synthesize_answers_for_course(
        run_id="run",
        course={
            "course_id": "24372",
            "title": "Time Series Analysis in Python",
            "metadata": {"level": "beginner", "subjects": ["python", "time series"]},
        },
        canonical_topics=[
            {
                "course_id": "24372",
                "canonical_topic_id": "ct_arima",
                "label": "ARIMA",
                "topic_type": "concept",
            }
        ],
        validations=[
            {
                "course_id": "24372",
                "question_id": "q1",
                "status": "accepted",
                "original_text": "What is ARIMA?",
                "final_text": "What is ARIMA?",
                "question_family": "entry",
                "relevant_topics": ["ARIMA"],
                "evidence_spans": [],
            }
        ],
        related_pairs=[],
        synth_client=synth_client,
        validate_client=validate_client,
        logger=logger,
    )

    validation = result.validations[0]
    assert validation.correctness == 1.0
    assert validation.sufficiency == 0.8
    assert validation.contradiction_risk == 0.2
    assert validation.scope_drift == 0.2
