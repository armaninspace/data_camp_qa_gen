from __future__ import annotations

from pathlib import Path
import json

from course_pipeline.pricing import fetch_live_pricing_snapshot
from course_pipeline.run_logging import RunLogger
from course_pipeline.run_logging import StageTimer
from course_pipeline.tasks.render import publish_final_outputs


def test_publish_final_outputs_merges_and_logs(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    final_dir = tmp_path / "final"
    (run_dir / "course_yaml").mkdir(parents=True)

    artifacts = {
        "normalized_courses.jsonl": '{"course_id": "1", "title": "One"}\n',
        "course_context_frames.jsonl": '{"course_id": "1", "course_title": "One", "domain": "python", "primary_tools": [], "core_tasks": [], "scope_bias": [], "answer_style": {"depth": "introductory", "tone": "direct", "prefer_examples": true, "prefer_definitions": true, "keep_short": true}}\n',
        "question_context_frames.jsonl": '{"question_id": "q1", "course_id": "1", "question_text": "What is t1?", "question_intent": "definition", "relevant_topics": ["t1"], "chapter_scope": [], "expected_answer_shape": ["short definition"], "scope_bias": [], "support_refs": []}\n',
        "train_rows.jsonl": '{"row_id": "1:q1:a:1", "course_id": "1", "question_id": "q1", "question_text": "What is t1?", "provided_context": {"course_context_frame": {"course_id": "1", "course_title": "One", "domain": "python", "primary_tools": [], "core_tasks": [], "scope_bias": [], "answer_style": {"depth": "introductory", "tone": "direct", "prefer_examples": true, "prefer_definitions": true, "keep_short": true}}, "question_context_frame": {"question_id": "q1", "course_id": "1", "question_text": "What is t1?", "question_intent": "definition", "relevant_topics": ["t1"], "chapter_scope": [], "expected_answer_shape": ["short definition"], "scope_bias": [], "support_refs": []}}, "teacher_answer": "answer", "question_variants": ["What is t1?"], "answer_quality_flags": {"course_aligned": true, "weak_grounding": false, "off_topic": false, "duplicate_signature": "what is t1", "cache_eligible": true, "train_eligible": true, "needs_review": false}, "global_question_signature": "what is t1", "cross_course_similarity": []}\n',
        "cache_rows.jsonl": '{"cache_key": "1::what is t1", "course_id": "1", "question_text": "What is t1?", "question_variants": ["What is t1?"], "provided_context": {"course_context_frame": {"course_id": "1", "course_title": "One", "domain": "python", "primary_tools": [], "core_tasks": [], "scope_bias": [], "answer_style": {"depth": "introductory", "tone": "direct", "prefer_examples": true, "prefer_definitions": true, "keep_short": true}}, "question_context_frame": {"question_id": "q1", "course_id": "1", "question_text": "What is t1?", "question_intent": "definition", "relevant_topics": ["t1"], "chapter_scope": [], "expected_answer_shape": ["short definition"], "scope_bias": [], "support_refs": []}}, "canonical_answer": "answer", "cache_eligible": true, "global_question_signature": "what is t1", "cross_course_similarity": []}\n',
        "semantic_topics.jsonl": '{"course_id": "1", "label": "t1"}\n',
        "semantic_correlated_topics.jsonl": '{"course_id": "1", "topics": ["t1", "t2"]}\n',
        "semantic_topic_questions.jsonl": '{"course_id": "1", "question_id": "q1"}\n',
        "semantic_correlated_topic_questions.jsonl": '{"course_id": "1", "question_id": "q2"}\n',
        "semantic_synthetic_answers.jsonl": '{"course_id": "1", "question_text": "What is t1?"}\n',
        "semantic_review_decisions.jsonl": '{"course_id": "1", "target_id": "q1", "decision": "keep"}\n',
        "answers.jsonl": '{"course_id": "1", "question_id": "q1", "correctness": "correct", "answer_text": "answer", "answer_mode": "synthetic_tutor_answer", "validation_status": "accept", "evidence": [{"source": "overview", "text": "answer"}]}\n',
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
    assert summary["course_context_frame_count"] == 1
    assert summary["question_context_frame_count"] == 1
    assert summary["train_row_count"] == 1
    assert summary["cache_row_count"] == 1
    assert summary["semantic_answer_count"] == 1
    assert summary["review_decision_count"] == 1
    assert (final_dir / "course_yaml" / "1.yaml").exists()
    assert (final_dir / "semantic_synthetic_answers.jsonl").exists()
    publish_log = (run_dir / "logs" / "publish.log").read_text(encoding="utf-8")
    assert "publish complete" in publish_log


def test_llm_log_shape(tmp_path: Path) -> None:
    logger = RunLogger(run_id="run", root_dir=tmp_path)
    logger.ensure_files()
    logger.write_pricing_snapshot(
        fetch_live_pricing_snapshot(
            fetch_text=lambda url: """
            <h2>GPT-5.4</h2>
            <p>Input:</p><p>$2.50 / 1M tokens</p>
            <p>Cached input:</p><p>$0.25 / 1M tokens</p>
            <p>Output:</p><p>$15.00 / 1M tokens</p>
            """,
            fetched_at="2026-04-21T00:00:00+00:00",
        )
    )
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
        cached_tokens_in=4,
        tokens_out=20,
        retry_count=0,
        status="success",
    )

    payload = (tmp_path / "logs" / "llm_calls.jsonl").read_text(encoding="utf-8")
    assert '"actual_model_source": "response.model"' in payload
    assert '"actual_model": "gpt-5.4-2025-01-01"' in payload
    assert '"cached_tokens_in": 4' in payload
    assert '"resolved_pricing_model": "gpt-5.4"' in payload
    assert '"cost_status": "ok"' in payload


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
