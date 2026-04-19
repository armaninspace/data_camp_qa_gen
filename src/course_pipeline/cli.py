from __future__ import annotations

import json
from pathlib import Path
import random
import shutil
import time

import typer

from course_pipeline.config import Settings
from course_pipeline.flows.course_question_pipeline import course_question_pipeline_flow
from course_pipeline.io_utils import read_jsonl, read_yaml, write_jsonl, write_yaml
from course_pipeline.llm import LLMClient
from course_pipeline.run_logging import RunLogger
from course_pipeline.tasks.synthesize_answers import (
    build_fine_tune_rows_from_artifacts,
    render_ft_bundles,
    run_synthetic_answering,
)

app = typer.Typer(help="Course question pipeline CLI. `run` is the primary path.")
ARTIFACT_FILES = [
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
]


def _require_numeric_bundle_id(bundle_id: str) -> str:
    if not bundle_id.isdigit():
        raise typer.BadParameter("bundle_id must contain digits only, e.g. 0, 1, 2, 011")
    return bundle_id


def _parse_publish_value(value: str) -> bool:
    normalized = value.strip().lower()
    truthy_values = {"1", "true", "t", "yes", "y", "on"}
    falsy_values = {"0", "false", "f", "no", "n", "off"}
    if normalized in truthy_values:
        return True
    if normalized in falsy_values:
        return False
    raise typer.BadParameter(
        "publish must be a boolean string such as true/false, 1/0, yes/no"
    )


def _course_id_for_row(row: dict) -> str | None:
    if row.get("course_id") is not None:
        return str(row["course_id"])
    course = row.get("course")
    if isinstance(course, dict) and course.get("course_id") is not None:
        return str(course["course_id"])
    return None


def _filter_rows_by_course_ids(rows: list[dict], course_ids: set[str]) -> list[dict]:
    return [row for row in rows if _course_id_for_row(row) in course_ids]


def _bundle_log(bundle_dir: Path, message: str) -> None:
    log_path = bundle_dir / "inspectgion_bundle.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def _random_inspectgion_selection(
    source_dir: Path,
    bundle_id: str,
    *,
    course_count: int = 4,
) -> list[dict[str, str | None]]:
    course_yaml_dir = source_dir / "course_yaml"
    bundle_files = sorted(course_yaml_dir.glob("*.yaml"))
    if len(bundle_files) < course_count:
        raise RuntimeError(
            f"need at least {course_count} published course bundles in data/final; found {len(bundle_files)}"
        )

    rng = random.Random(int(bundle_id))
    selected_paths = sorted(rng.sample(bundle_files, course_count), key=lambda item: item.stem)

    selected_courses: list[dict[str, str | None]] = []
    for path in selected_paths:
        payload = read_yaml(path) or {}
        selected_courses.append(
            {
                "course_id": str(payload.get("course_id", path.stem)),
                "title": payload.get("title"),
                "slug": None,
                "language": None,
            }
        )
    return selected_courses


@app.command()
def run(
    input: str = typer.Option(..., help="Input directory of scraped courses."),
    output: str = typer.Option(..., help="Transient run directory."),
    final_dir: str = typer.Option("data/final", help="Published final output directory."),
    slice_start: float = typer.Option(0.0, min=0.0, max=100.0, help="Slice start percent."),
    slice_end: float = typer.Option(100.0, min=0.0, max=100.0, help="Slice end percent."),
    publish: str = typer.Option(
        "true",
        "--publish",
        help="Publish merged outputs to data/final. Accepts true/false.",
    ),
    no_publish: bool = typer.Option(
        False,
        "--no-publish",
        help="Disable publish-to-data/final for this run.",
    ),
) -> None:
    publish_enabled = False if no_publish else _parse_publish_value(publish)
    result = course_question_pipeline_flow(
        input_dir=input,
        output_dir=output,
        final_dir=final_dir,
        slice_start=slice_start,
        slice_end=slice_end,
        publish=publish_enabled,
    )
    typer.echo(
        json.dumps(
            {
                "selected_course_count": result["selected_course_count"],
                "run_course_count": result["run_summary"]["course_count"],
                "published_course_count": (
                    None
                    if result["published_summary"] is None
                    else result["published_summary"]["course_count"]
                ),
            },
            indent=2,
        )
    )


@app.command("run-synthetic-answering")
def run_synthetic_answering_command(
    run_dir: str = typer.Option(..., help="Run directory containing validated question artifacts."),
    output_dir: str | None = typer.Option(
        None,
        help="Debug output directory for synthetic artifacts. Defaults to run_dir.",
    ),
) -> None:
    settings = Settings()
    logger = RunLogger(run_id=Path(run_dir).name, root_dir=Path(run_dir))
    logger.ensure_files()
    result = run_synthetic_answering(
        run_dir=run_dir,
        output_dir=output_dir,
        synth_client=LLMClient(
            api_key=settings.openai_api_key,
            model=settings.model_synth_answer,
        ),
        validate_client=LLMClient(
            api_key=settings.openai_api_key,
            model=settings.model_synth_validate,
        ),
        logger=logger,
    )
    typer.echo(
        json.dumps(
            {
                "synthetic_answer_count": len(result.synthetic_answers),
                "validation_count": len(result.validations),
                "rewrite_count": len(result.rewrites),
                "fine_tune_row_count": len(result.fine_tune_rows),
            },
            indent=2,
        )
    )


@app.command("build-ft-dataset")
def build_ft_dataset_command(
    run_dir: str = typer.Option(..., help="Run directory containing synthetic answer artifacts."),
    output_dir: str | None = typer.Option(
        None,
        help="Debug output directory for FT dataset artifacts. Defaults to run_dir.",
    ),
) -> None:
    rows = build_fine_tune_rows_from_artifacts(run_dir=run_dir, output_dir=output_dir)
    typer.echo(json.dumps({"fine_tune_row_count": len(rows)}, indent=2))


@app.command("render-ft-bundle")
def render_ft_bundle_command(
    run_dir: str = typer.Option(..., help="Run directory containing synthetic answer artifacts."),
    output_dir: str | None = typer.Option(
        None,
        help="Debug output directory for FT bundle YAMLs. Defaults to run_dir.",
    ),
) -> None:
    bundles = render_ft_bundles(run_dir=run_dir, output_dir=output_dir)
    typer.echo(json.dumps({"course_bundle_count": len(bundles)}, indent=2))


@app.command("mk_inspectgion_bundle")
def mk_inspectgion_bundle(
    bundle_id: str = typer.Argument(..., help="Digits-only bundle id such as 0, 1, or 011."),
    final_dir: str = typer.Option(
        "data/final",
        help="Directory containing published final pipeline outputs.",
    ),
    tmp_root: str = typer.Option(
        "/tmp",
        help="Root directory where the inspectgion bundle folder will be created.",
    ),
) -> None:
    bundle_id = _require_numeric_bundle_id(bundle_id)
    start = time.perf_counter()
    source_dir = Path(final_dir)
    if not source_dir.exists():
        raise typer.BadParameter(f"final_dir does not exist: {source_dir}")

    bundle_dir = Path(tmp_root) / f"inspectgion_bundl_{bundle_id}"
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    selected_courses = _random_inspectgion_selection(source_dir, bundle_id)
    selected_course_ids = {str(item["course_id"]) for item in selected_courses}
    missing_course_ids = [
        course_id
        for course_id in sorted(selected_course_ids)
        if not (source_dir / "course_yaml" / f"{course_id}.yaml").exists()
    ]
    if missing_course_ids:
        raise RuntimeError(
            f"missing required selected course outputs in data/final: {', '.join(missing_course_ids)}"
        )

    _bundle_log(bundle_dir, f"bundle start bundle_id={bundle_id} source_dir={source_dir}")
    artifact_counts: dict[str, dict[str, int]] = {}
    for artifact_name in ARTIFACT_FILES:
        source_rows = read_jsonl(source_dir / artifact_name)
        selected_rows = _filter_rows_by_course_ids(source_rows, selected_course_ids)
        write_jsonl(bundle_dir / artifact_name, selected_rows)
        artifact_counts[artifact_name] = {
            "selected_row_count": len(selected_rows),
            "source_row_count": len(source_rows),
        }
        _bundle_log(
            bundle_dir,
            f"artifact filtered name={artifact_name} selected_rows={len(selected_rows)} source_rows={len(source_rows)}",
        )

    selected_yaml_count = 0
    for item in selected_courses:
        source_yaml = source_dir / "course_yaml" / f"{item['course_id']}.yaml"
        target_yaml = bundle_dir / "course_yaml" / f"{item['course_id']}.yaml"
        target_yaml.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_yaml, target_yaml)
        selected_yaml_count += 1

    artifact_counts["course_yaml"] = {
        "selected_file_count": selected_yaml_count,
        "expected_file_count": len(selected_courses),
    }

    run_summary = read_yaml(source_dir / "run_summary.yaml")
    if run_summary:
        write_yaml(bundle_dir / "run_summary.yaml", run_summary)

    elapsed = round(time.perf_counter() - start, 3)
    manifest = {
        "bundle_id": bundle_id,
        "bundle_dir": str(bundle_dir),
        "source_final_dir": str(source_dir),
        "selection_policy": {
            "description": "Four published courses selected at random from data/final, reproducible by bundle_id seed.",
            "selection_seed": int(bundle_id),
            "selected_courses": selected_courses,
        },
        "artifact_counts": artifact_counts,
        "performance_data": {
            "bundle_build_seconds": elapsed,
            "published_run_course_count": run_summary.get("course_count"),
        },
        "log_ownership": {
            "bundle_log_path": str(bundle_dir / "inspectgion_bundle.log"),
            "scope": "bundle_scoped",
        },
    }
    write_yaml(bundle_dir / "pipeline_run_manifest.yaml", manifest)
    _bundle_log(bundle_dir, f"bundle complete bundle_id={bundle_id} elapsed_seconds={elapsed}")
    typer.echo(str(bundle_dir))


if __name__ == "__main__":
    app()
