from __future__ import annotations

from pathlib import Path
import json

from typer.testing import CliRunner

from course_pipeline import cli
from course_pipeline.cli import app


def _write_final_fixture(root: Path, course_id: str) -> None:
    (root / "course_yaml").mkdir(parents=True, exist_ok=True)
    for artifact_name in [
        "normalized_courses.jsonl",
        "course_context_frames.jsonl",
        "question_context_frames.jsonl",
        "train_rows.jsonl",
        "cache_rows.jsonl",
        "semantic_topics.jsonl",
        "semantic_correlated_topics.jsonl",
        "semantic_topic_questions.jsonl",
        "semantic_correlated_topic_questions.jsonl",
        "semantic_synthetic_answers.jsonl",
        "semantic_review_decisions.jsonl",
        "answers.jsonl",
        "all_rows.jsonl",
    ]:
        with (root / artifact_name).open("a", encoding="utf-8") as handle:
            if artifact_name == "course_context_frames.jsonl":
                handle.write(
                    f'{{"course_id": "{course_id}", "course_title": "Title {course_id}", "learner_level": "beginner", "domain": "python", "primary_tools": [], "core_tasks": [], "scope_bias": [], "answer_style": {{"depth": "introductory", "tone": "direct", "prefer_examples": true, "prefer_definitions": true, "keep_short": true}}}}\n'
                )
            elif artifact_name == "question_context_frames.jsonl":
                handle.write(
                    f'{{"question_id": "q_{course_id}", "course_id": "{course_id}", "question_text": "What is topic {course_id}?", "question_intent": "definition", "relevant_topics": ["topic {course_id}"], "chapter_scope": [], "expected_answer_shape": ["short definition"], "scope_bias": [], "support_refs": []}}\n'
                )
            elif artifact_name == "train_rows.jsonl":
                handle.write(
                    f'{{"row_id": "{course_id}:q_{course_id}:a:1", "course_id": "{course_id}", "question_id": "q_{course_id}", "question_text": "What is topic {course_id}?", "provided_context": {{"course_context_frame": {{"course_id": "{course_id}", "course_title": "Title {course_id}", "learner_level": "beginner", "domain": "python", "primary_tools": [], "core_tasks": [], "scope_bias": [], "answer_style": {{"depth": "introductory", "tone": "direct", "prefer_examples": true, "prefer_definitions": true, "keep_short": true}}}}, "question_context_frame": {{"question_id": "q_{course_id}", "course_id": "{course_id}", "question_text": "What is topic {course_id}?", "question_intent": "definition", "relevant_topics": ["topic {course_id}"], "chapter_scope": [], "expected_answer_shape": ["short definition"], "scope_bias": [], "support_refs": []}}}}, "answer_text": "Answer {course_id}", "question_variants": ["What is topic {course_id}?"], "answer_quality_flags": {{"course_aligned": true, "weak_grounding": false, "off_topic": false, "duplicate_signature": "what is topic {course_id}", "cache_eligible": true, "train_eligible": true, "needs_review": false}}, "global_question_signature": "what is topic {course_id}", "cross_course_similarity": []}}\n'
                )
            elif artifact_name == "cache_rows.jsonl":
                handle.write(
                    f'{{"cache_key": "{course_id}::what is topic {course_id}", "course_id": "{course_id}", "question_text": "What is topic {course_id}?", "question_variants": ["What is topic {course_id}?"], "provided_context": {{"course_context_frame": {{"course_id": "{course_id}", "course_title": "Title {course_id}", "learner_level": "beginner", "domain": "python", "primary_tools": [], "core_tasks": [], "scope_bias": [], "answer_style": {{"depth": "introductory", "tone": "direct", "prefer_examples": true, "prefer_definitions": true, "keep_short": true}}}}, "question_context_frame": {{"question_id": "q_{course_id}", "course_id": "{course_id}", "question_text": "What is topic {course_id}?", "question_intent": "definition", "relevant_topics": ["topic {course_id}"], "chapter_scope": [], "expected_answer_shape": ["short definition"], "scope_bias": [], "support_refs": []}}}}, "canonical_answer": "Answer {course_id}", "cache_eligible": true, "global_question_signature": "what is topic {course_id}", "cross_course_similarity": []}}\n'
                )
            elif artifact_name == "semantic_topic_questions.jsonl":
                handle.write(f'{{"course_id": "{course_id}", "question_id": "q_{course_id}"}}\n')
            elif artifact_name == "semantic_synthetic_answers.jsonl":
                handle.write(f'{{"course_id": "{course_id}", "question_text": "What is topic {course_id}?"}}\n')
            elif artifact_name == "answers.jsonl":
                handle.write(
                    f'{{"course_id": "{course_id}", "question_id": "q_{course_id}", "question_text": "What is topic {course_id}?", "answer_text": "Answer {course_id}", "correctness": "correct", "answer_mode": "synthetic_tutor_answer", "validation_status": "accept"}}\n'
                )
            elif artifact_name == "all_rows.jsonl":
                handle.write(
                    f'{{"row_id": "r_{course_id}", "question_id": "q_{course_id}", "course": {{"course_id": "{course_id}", "title": "Title {course_id}"}}, "relevant_topics": ["topic {course_id}"], "question_text": "What is topic {course_id}?", "question_answer": "Answer {course_id}", "correctness": "correct", "question_family": "what_is", "status": "answered"}}\n'
                )
            else:
                handle.write(f'{{"course_id": "{course_id}"}}\n')
    (root / "course_yaml" / f"{course_id}.yaml").write_text(
        (
            f"course_id: '{course_id}'\n"
            f"title: Title {course_id}\n"
            "answers:\n"
            f"  - question_id: q_{course_id}\n"
            f"    question_text: What is topic {course_id}?\n"
            f"    answer_text: Answer {course_id}\n"
            "    answer_mode: synthetic_tutor_answer\n"
            "final_rows:\n"
            f"  - row_id: r_{course_id}\n"
            f"    question_id: q_{course_id}\n"
            f"    course:\n"
            f"      course_id: '{course_id}'\n"
            f"      title: Title {course_id}\n"
            f"    relevant_topics:\n"
            f"      - topic {course_id}\n"
            f"    question_text: What is topic {course_id}?\n"
            f"    question_answer: Answer {course_id}\n"
            "    correctness: correct\n"
            "    question_family: what_is\n"
            "    status: answered\n"
        ),
        encoding="utf-8",
    )


def test_mk_inspectgion_bundle_filters_selected_courses(tmp_path: Path) -> None:
    final_dir = tmp_path / "final"
    for course_id in ("20001", "20002", "20003", "20004", "20005"):
        _write_final_fixture(final_dir, course_id)
    (final_dir / "run_summary.yaml").write_text("course_count: 5\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "mk_inspectgion_bundle",
            "0",
            "--final-dir",
            str(final_dir),
            "--tmp-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    bundle_dir = tmp_path / "inspectgion_bundl_0"
    manifest = (bundle_dir / "pipeline_run_manifest.yaml").read_text(encoding="utf-8")
    assert "published_run_course_count: 5" in manifest
    assert "export_mode: filtered" in manifest
    assert "selection_seed" not in manifest
    assert (bundle_dir / "inspectgion_bundle.log").exists()
    assert (bundle_dir / "bundle_validation.json").exists()
    assert (bundle_dir / "bundle_validation.md").exists()
    assert (bundle_dir / "semantic_topics.jsonl").exists()
    assert (bundle_dir / "semantic_synthetic_answers.jsonl").exists()
    selected_files = sorted(path.stem for path in (bundle_dir / "course_yaml").glob("*.yaml"))
    assert len(selected_files) == 4
    assert set(selected_files).issubset({"20001", "20002", "20003", "20004", "20005"})
    bundle_summary = (bundle_dir / "run_summary.yaml").read_text(encoding="utf-8")
    assert "course_count: 4" in bundle_summary
    bundled_answer_courses = {
        json.loads(line)["course_id"]
        for line in (bundle_dir / "answers.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    bundled_row_courses = {
        json.loads(line)["course"]["course_id"]
        for line in (bundle_dir / "all_rows.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    assert bundled_answer_courses == set(selected_files)
    assert bundled_row_courses == set(selected_files)
    validation = json.loads((bundle_dir / "bundle_validation.json").read_text(encoding="utf-8"))
    assert validation["status"] == "pass"
    assert validation["expected_course_ids"] == selected_files
    validation_md = (bundle_dir / "bundle_validation.md").read_text(encoding="utf-8")
    assert "# Bundle Validation" in validation_md
    assert "`status`: `pass`" in validation_md
    bundle_log = (bundle_dir / "inspectgion_bundle.log").read_text(encoding="utf-8")
    assert "bundle selection selected_course_ids=" in bundle_log


def test_run_accepts_publish_boolean_string_and_flag_forms(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured_publish_values: list[bool] = []

    def _fake_flow(**kwargs: object) -> dict[str, object]:
        captured_publish_values.append(bool(kwargs["publish"]))
        return {
            "selected_course_count": 0,
            "run_summary": {"course_count": 0},
            "published_summary": None,
        }

    monkeypatch.setattr(cli, "course_question_pipeline_flow", _fake_flow)
    runner = CliRunner()

    default_result = runner.invoke(
        app,
        [
            "run",
            "--input",
            str(tmp_path),
            "--output",
            str(tmp_path / "run-default"),
        ],
    )
    assert default_result.exit_code == 0, default_result.output

    false_result = runner.invoke(
        app,
        [
            "run",
            "--input",
            str(tmp_path),
            "--output",
            str(tmp_path / "run-false"),
            "--publish",
            "false",
        ],
    )
    assert false_result.exit_code == 0, false_result.output

    no_publish_result = runner.invoke(
        app,
        [
            "run",
            "--input",
            str(tmp_path),
            "--output",
            str(tmp_path / "run-no-publish"),
            "--no-publish",
        ],
    )
    assert no_publish_result.exit_code == 0, no_publish_result.output

    assert captured_publish_values == [True, False, False]
