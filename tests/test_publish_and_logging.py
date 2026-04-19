from __future__ import annotations

from pathlib import Path

from course_pipeline.run_logging import RunLogger
from course_pipeline.tasks.render import publish_final_outputs


def test_publish_final_outputs_merges_and_logs(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    final_dir = tmp_path / "final"
    (run_dir / "course_yaml").mkdir(parents=True)

    artifacts = {
        "normalized_courses.jsonl": '{"course_id": "1", "title": "One"}\n',
        "topics.jsonl": '{"course_id": "1", "topic_id": "t1"}\n',
        "canonical_topics.jsonl": '{"course_id": "1", "canonical_topic_id": "ct1"}\n',
        "question_candidates.jsonl": '{"course_id": "1", "candidate_id": "q1"}\n',
        "question_repairs.jsonl": '{"course_id": "1", "candidate_id": "q1"}\n',
        "answers.jsonl": '{"course_id": "1", "question_id": "q1"}\n',
        "all_rows.jsonl": '{"course": {"course_id": "1", "title": "One"}, "status": "answered"}\n',
    }
    for name, content in artifacts.items():
        (run_dir / name).write_text(content, encoding="utf-8")
    (run_dir / "course_yaml" / "1.yaml").write_text(
        "course_id: '1'\ntitle: One\nfinal_rows:\n  - status: answered\n",
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
    assert (final_dir / "course_yaml" / "1.yaml").exists()
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
