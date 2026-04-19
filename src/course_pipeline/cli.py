from __future__ import annotations

import json
from pathlib import Path
import shutil
import time

import typer

from course_pipeline.flows.course_question_pipeline import course_question_pipeline_flow
from course_pipeline.io_utils import read_jsonl, read_yaml, write_jsonl, write_yaml

app = typer.Typer(help="Course question pipeline CLI.")

INSPECTGION_SELECTION = [
    {
        "course_id": "24511",
        "slug": "0143-datacamp-categorical-data-in-the-tidyverse-24511-904060391f75",
        "language": "R",
        "title": "Categorical Data in the Tidyverse",
    },
    {
        "course_id": "24662",
        "slug": "0294-datacamp-intermediate-functional-programming-with-purrr-24662-3f669a54b183",
        "language": "R",
        "title": "Intermediate Functional Programming with purrr",
    },
    {
        "course_id": "24516",
        "slug": "0148-datacamp-improving-query-performance-in-sql-server-24516-db81d1568bd3",
        "language": "SQL",
        "title": "Improving Query Performance in SQL Server",
    },
    {
        "course_id": "24458",
        "slug": "0090-datacamp-time-series-analysis-in-python-24458-da389c14f72d",
        "language": "Python",
        "title": "Time Series Analysis in Python",
    },
]
ARTIFACT_FILES = [
    "normalized_courses.jsonl",
    "topics.jsonl",
    "canonical_topics.jsonl",
    "question_candidates.jsonl",
    "question_repairs.jsonl",
    "answers.jsonl",
    "all_rows.jsonl",
]


def _require_numeric_bundle_id(bundle_id: str) -> str:
    if not bundle_id.isdigit():
        raise typer.BadParameter("bundle_id must contain digits only, e.g. 0, 1, 2, 011")
    return bundle_id


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


@app.command()
def run(
    input: str = typer.Option(..., help="Input directory of scraped courses."),
    output: str = typer.Option(..., help="Transient run directory."),
    final_dir: str = typer.Option("data/final", help="Published final output directory."),
    slice_start: float = typer.Option(0.0, min=0.0, max=100.0, help="Slice start percent."),
    slice_end: float = typer.Option(100.0, min=0.0, max=100.0, help="Slice end percent."),
    publish: bool = typer.Option(True, help="Publish merged outputs to data/final."),
) -> None:
    result = course_question_pipeline_flow(
        input_dir=input,
        output_dir=output,
        final_dir=final_dir,
        slice_start=slice_start,
        slice_end=slice_end,
        publish=publish,
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

    selected_course_ids = {item["course_id"] for item in INSPECTGION_SELECTION}
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
    for item in INSPECTGION_SELECTION:
        source_yaml = source_dir / "course_yaml" / f"{item['course_id']}.yaml"
        target_yaml = bundle_dir / "course_yaml" / f"{item['course_id']}.yaml"
        target_yaml.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_yaml, target_yaml)
        selected_yaml_count += 1

    artifact_counts["course_yaml"] = {
        "selected_file_count": selected_yaml_count,
        "expected_file_count": len(INSPECTGION_SELECTION),
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
            "description": "Fixed four-course inspection set with intermediate concepts: 2 R, 1 SQL, 1 Python.",
            "selected_courses": INSPECTGION_SELECTION,
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
