from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

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
    for course_id in ("24511", "24662", "24516", "24458"):
        _write_final_fixture(final_dir, course_id)
    (final_dir / "run_summary.yaml").write_text("course_count: 4\n", encoding="utf-8")

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
    assert "published_run_course_count: 4" in manifest
    assert (bundle_dir / "inspectgion_bundle.log").exists()
