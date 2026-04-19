from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from course_pipeline import cli
from course_pipeline.cli import app


def _write_final_fixture(root: Path, course_id: str) -> None:
    (root / "course_yaml").mkdir(parents=True, exist_ok=True)
    for artifact_name in [
        "normalized_courses.jsonl",
        "topics.jsonl",
        "canonical_topics.jsonl",
        "related_topic_pairs.jsonl",
        "vetted_topics.jsonl",
        "vetted_topic_pairs.jsonl",
        "single_topic_questions.jsonl",
        "pairwise_questions.jsonl",
        "question_validation.jsonl",
        "question_candidates.jsonl",
        "question_repairs.jsonl",
        "answers.jsonl",
        "synthetic_answers.jsonl",
        "synthetic_answer_validation.jsonl",
        "synthetic_answer_rewrites.jsonl",
        "all_rows.jsonl",
    ]:
        with (root / artifact_name).open("a", encoding="utf-8") as handle:
            if artifact_name == "all_rows.jsonl":
                handle.write(
                    f'{{"course": {{"course_id": "{course_id}", "title": "Title {course_id}"}}, "status": "answered"}}\n'
                )
            else:
                handle.write(f'{{"course_id": "{course_id}"}}\n')
    (root / "course_yaml" / f"{course_id}.yaml").write_text(
        f"course_id: '{course_id}'\ntitle: Title {course_id}\nfinal_rows:\n  - status: answered\n",
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
    assert "selection_seed: 0" in manifest
    assert (bundle_dir / "inspectgion_bundle.log").exists()
    assert (bundle_dir / "synthetic_answers.jsonl").exists()
    assert (bundle_dir / "synthetic_answer_validation.jsonl").exists()
    selected_files = sorted(path.stem for path in (bundle_dir / "course_yaml").glob("*.yaml"))
    assert len(selected_files) == 4
    assert set(selected_files).issubset({"20001", "20002", "20003", "20004", "20005"})


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
