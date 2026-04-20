from __future__ import annotations

from pathlib import Path
import json

from course_pipeline.run_logging import RunLogger
from course_pipeline.run_logging import StageTimer
from course_pipeline.tasks.render import publish_final_outputs


def test_publish_final_outputs_merges_and_logs(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    final_dir = tmp_path / "final"
    (run_dir / "course_yaml").mkdir(parents=True)

    artifacts = {
        "normalized_courses.jsonl": '{"course_id": "1", "title": "One"}\n',
        "topics.jsonl": '{"course_id": "1", "topic_id": "t1"}\n',
        "canonical_topics.jsonl": '{"course_id": "1", "canonical_topic_id": "ct1"}\n',
        "related_topic_pairs.jsonl": '{"course_id": "1", "pair_id": "p1"}\n',
        "vetted_topics.jsonl": '{"course_id": "1", "canonical_topic_id": "ct1", "decision": "keep"}\n',
        "vetted_topic_pairs.jsonl": '{"course_id": "1", "pair_id": "p1", "decision": "keep_pair"}\n',
        "single_topic_questions.jsonl": '{"course_id": "1", "question_id": "q1"}\n',
        "pairwise_questions.jsonl": '{"course_id": "1", "question_id": "q2"}\n',
        "question_validation.jsonl": '{"course_id": "1", "question_id": "q1", "status": "accepted"}\n',
        "question_candidates.jsonl": '{"course_id": "1", "candidate_id": "q1"}\n',
        "question_repairs.jsonl": '{"course_id": "1", "candidate_id": "q1"}\n',
        "answers.jsonl": '{"course_id": "1", "question_id": "q1", "correctness": "correct", "answer_text": "answer", "answer_mode": "synthetic_tutor_answer", "validation_status": "accept", "evidence": [{"source": "overview", "text": "answer"}]}\n',
        "synthetic_answers.jsonl": '{"run_id": "run", "course_id": "1", "question_id": "q1", "question_text": "What is t1?", "canonical_topic": "t1", "question_family": "entry", "difficulty_band": "beginner", "answer_mode": "synthetic_tutor_answer", "answer_text": "answer", "target_verbosity": "brief", "model_name": "gpt-5.4", "prompt_family": "synthesize_answer", "confidence": 0.9, "risks": []}\n',
        "synthetic_answer_validation.jsonl": '{"run_id": "run", "course_id": "1", "question_id": "q1", "original_answer_text": "answer", "decision": "accept", "correctness": 0.9, "sufficiency": 0.9, "brevity": 0.9, "pedagogical_fit": 0.9, "difficulty_alignment": 0.9, "clarity": 0.9, "contradiction_risk": 0.1, "scope_drift": 0.1, "rewritten_answer_text": null, "reject_reasons": []}\n',
        "synthetic_answer_rewrites.jsonl": "",
        "all_rows.jsonl": '{"course": {"course_id": "1", "title": "One"}, "status": "answered"}\n',
    }
    for name, content in artifacts.items():
        (run_dir / name).write_text(content, encoding="utf-8")
    (run_dir / "course_yaml" / "1.yaml").write_text(
        (
            "course_id: '1'\n"
            "title: One\n"
            "answers:\n"
            "  - question_id: q1\n"
            "    answer_mode: synthetic_tutor_answer\n"
            "final_rows:\n"
            "  - status: answered\n"
        ),
        encoding="utf-8",
    )

    logger = RunLogger(run_id="run", root_dir=run_dir)
    logger.ensure_files()
    summary = publish_final_outputs(
        run_dir=run_dir,
        final_dir=final_dir,
        affected_course_ids={"1"},
        logger=logger,
    )

    assert summary["course_count"] == 1
    assert summary["synthetic_answer_count"] == 1
    assert summary["synthetic_accepted_count"] == 1
    assert (final_dir / "course_yaml" / "1.yaml").exists()
    assert (final_dir / "synthetic_answers.jsonl").exists()
    publish_log = (run_dir / "logs" / "publish.log").read_text(encoding="utf-8")
    assert "publish complete" in publish_log


def test_llm_log_shape(tmp_path: Path) -> None:
    logger = RunLogger(run_id="run", root_dir=tmp_path)
    logger.ensure_files()
    logger.log_llm_call(
        course_id="1",
        stage="extract_atomic_topics",
        prompt_family="extract",
        configured_model="gpt-5.4",
        requested_model="gpt-5.4",
        actual_model="gpt-5.4-2025-01-01",
        actual_model_source="response.model",
        provider_request_id="req_1",
        latency_ms=123,
        tokens_in=10,
        tokens_out=20,
        retry_count=0,
        status="success",
    )

    payload = (tmp_path / "logs" / "llm_calls.jsonl").read_text(encoding="utf-8")
    assert '"actual_model_source": "response.model"' in payload
    assert '"actual_model": "gpt-5.4-2025-01-01"' in payload


def test_stage_metrics_log_started_and_completed_events(tmp_path: Path) -> None:
    logger = RunLogger(run_id="run", root_dir=tmp_path)
    logger.ensure_files()

    timer = StageTimer(
        logger,
        course_id="1",
        stage="extract_atomic_topics",
        input_row_count=3,
    )
    timer.finish(output_row_count=2, warning_count=1, error_count=0)

    payloads = [
        json.loads(line)
        for line in (tmp_path / "logs" / "stage_metrics.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [item["event"] for item in payloads] == ["started", "completed"]
    assert payloads[0]["duration_ms"] == 0
    assert payloads[0]["input_row_count"] == 3
    assert payloads[0]["output_row_count"] == 0
    assert payloads[1]["output_row_count"] == 2
    assert payloads[1]["warning_count"] == 1
