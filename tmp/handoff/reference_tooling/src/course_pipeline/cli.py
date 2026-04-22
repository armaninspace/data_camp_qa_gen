from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import random
import shutil
import time

import typer

from course_pipeline.config import Settings
from course_pipeline.flows.course_question_pipeline import course_question_pipeline_flow
from course_pipeline.io_utils import read_jsonl, read_yaml, write_jsonl, write_yaml
from course_pipeline.tasks.render import rebuild_run_summary

app = typer.Typer(help="Course question pipeline CLI. `run` is the primary path.")
ARTIFACT_FILES = [
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
]
QUESTION_SCOPED_ARTIFACTS = {
    "question_context_frames.jsonl",
    "semantic_topic_questions.jsonl",
    "semantic_correlated_topic_questions.jsonl",
    "answers.jsonl",
}


@dataclass(frozen=True)
class BundleSelection:
    bundle_id: str
    source_run_id: str | None
    export_mode: str
    selected_courses: list[dict[str, str | None]]
    selected_course_ids: list[str]
    selected_question_ids: list[str]
    selected_row_ids: list[str]
    selected_question_texts: list[str] = field(default_factory=list)
    selected_train_row_ids: list[str] = field(default_factory=list)
    selected_cache_keys: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ArtifactValidationResult:
    artifact_name: str
    expected_row_count: int
    observed_row_count: int
    expected_course_ids: list[str]
    observed_course_ids: list[str]
    missing_ids: list[str]
    unexpected_ids: list[str]
    status: str


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


def _question_id_for_row(row: dict) -> str | None:
    value = row.get("question_id")
    if value is None:
        return None
    return str(value)


def _row_id_for_row(row: dict) -> str | None:
    value = row.get("row_id")
    if value is None:
        return None
    return str(value)


def _cache_key_for_row(row: dict) -> str | None:
    value = row.get("cache_key")
    if value is None:
        return None
    return str(value)


def _question_text_for_row(row: dict) -> str | None:
    value = row.get("question_text")
    if value is None:
        return None
    return str(value)


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


def _full_bundle_selection(source_dir: Path) -> list[dict[str, str | None]]:
    selected_courses: list[dict[str, str | None]] = []
    for path in sorted((source_dir / "course_yaml").glob("*.yaml"), key=lambda item: item.stem):
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


def _build_bundle_selection(
    *,
    source_dir: Path,
    bundle_id: str,
    export_mode: str,
) -> BundleSelection:
    source_run_summary = read_yaml(source_dir / "run_summary.yaml")
    if export_mode == "full":
        selected_courses = _full_bundle_selection(source_dir)
    else:
        selected_courses = _random_inspectgion_selection(source_dir, bundle_id)

    selected_course_ids = sorted({str(item["course_id"]) for item in selected_courses})
    question_context_rows = _filter_rows_by_course_ids(
        read_jsonl(source_dir / "question_context_frames.jsonl"),
        set(selected_course_ids),
    )
    selected_question_ids = sorted(
        {
            question_id
            for row in question_context_rows
            for question_id in [_question_id_for_row(row)]
            if question_id is not None
        }
    )
    selected_question_texts = sorted(
        {
            question_text
            for row in question_context_rows
            for question_text in [_question_text_for_row(row)]
            if question_text is not None
        }
    )
    all_rows = _filter_rows_for_bundle(
        read_jsonl(source_dir / "all_rows.jsonl"),
        "all_rows.jsonl",
        selected_course_ids=set(selected_course_ids),
        selected_question_ids=set(selected_question_ids),
        selected_question_texts=set(selected_question_texts),
        selected_row_ids=set(),
        selected_train_row_ids=set(),
        selected_cache_keys=set(),
    )
    selected_row_ids = sorted(
        {
            row_id
            for row in all_rows
            for row_id in [_row_id_for_row(row)]
            if row_id is not None
        }
    )
    train_rows = _filter_rows_for_bundle(
        read_jsonl(source_dir / "train_rows.jsonl"),
        "train_rows.jsonl",
        selected_course_ids=set(selected_course_ids),
        selected_question_ids=set(selected_question_ids),
        selected_question_texts=set(selected_question_texts),
        selected_row_ids=set(selected_row_ids),
        selected_train_row_ids=set(),
        selected_cache_keys=set(),
    )
    selected_train_row_ids = sorted(
        {
            row_id
            for row in train_rows
            for row_id in [_row_id_for_row(row)]
            if row_id is not None
        }
    )
    cache_rows = _filter_rows_for_bundle(
        read_jsonl(source_dir / "cache_rows.jsonl"),
        "cache_rows.jsonl",
        selected_course_ids=set(selected_course_ids),
        selected_question_ids=set(selected_question_ids),
        selected_question_texts=set(selected_question_texts),
        selected_row_ids=set(selected_row_ids),
        selected_train_row_ids=set(selected_train_row_ids),
        selected_cache_keys=set(),
    )
    selected_cache_keys = sorted(
        {
            cache_key
            for row in cache_rows
            for cache_key in [_cache_key_for_row(row)]
            if cache_key is not None
        }
    )
    return BundleSelection(
        bundle_id=bundle_id,
        source_run_id=(
            None
            if not source_run_summary
            else str(source_run_summary.get("run_id") or source_dir.name)
        ),
        export_mode=export_mode,
        selected_courses=selected_courses,
        selected_course_ids=selected_course_ids,
        selected_question_ids=selected_question_ids,
        selected_row_ids=selected_row_ids,
        selected_question_texts=selected_question_texts,
        selected_train_row_ids=selected_train_row_ids,
        selected_cache_keys=selected_cache_keys,
    )


def _filter_rows_for_bundle(
    rows: list[dict],
    artifact_name: str,
    *,
    selected_course_ids: set[str],
    selected_question_ids: set[str],
    selected_question_texts: set[str],
    selected_row_ids: set[str],
    selected_train_row_ids: set[str],
    selected_cache_keys: set[str],
) -> list[dict]:
    filtered = _filter_rows_by_course_ids(rows, selected_course_ids)
    if artifact_name in QUESTION_SCOPED_ARTIFACTS:
        return [
            row for row in filtered if _question_id_for_row(row) in selected_question_ids
        ]
    if artifact_name == "all_rows.jsonl":
        if not selected_row_ids:
            return filtered
        return [row for row in filtered if _row_id_for_row(row) in selected_row_ids]
    if artifact_name == "train_rows.jsonl":
        if not selected_train_row_ids:
            return [
                row for row in filtered if _question_id_for_row(row) in selected_question_ids
            ]
        return [
            row
            for row in filtered
            if _row_id_for_row(row) in selected_train_row_ids
            and _question_id_for_row(row) in selected_question_ids
        ]
    if artifact_name == "cache_rows.jsonl":
        if not selected_cache_keys:
            return [
                row for row in filtered if _question_text_for_row(row) in selected_question_texts
            ]
        return [row for row in filtered if _cache_key_for_row(row) in selected_cache_keys]
    if artifact_name == "semantic_synthetic_answers.jsonl":
        return [
            row for row in filtered if _question_text_for_row(row) in selected_question_texts
        ]
    return filtered


def _expected_ids_for_artifact(artifact_name: str, rows: list[dict]) -> list[str]:
    if artifact_name in QUESTION_SCOPED_ARTIFACTS:
        return sorted(
            {
                question_id
                for row in rows
                for question_id in [_question_id_for_row(row)]
                if question_id is not None
            }
        )
    if artifact_name == "all_rows.jsonl":
        return sorted(
            {
                row_id
                for row in rows
                for row_id in [_row_id_for_row(row)]
                if row_id is not None
            }
        )
    if artifact_name == "train_rows.jsonl":
        return sorted(
            {
                row_id
                for row in rows
                for row_id in [_row_id_for_row(row)]
                if row_id is not None
            }
        )
    if artifact_name == "cache_rows.jsonl":
        return sorted(
            {
                cache_key
                for row in rows
                for cache_key in [_cache_key_for_row(row)]
                if cache_key is not None
            }
        )
    return []


def _validate_bundle_artifacts(
    *,
    bundle_dir: Path,
    selection: BundleSelection,
    expected_rows_by_artifact: dict[str, list[dict]],
) -> dict[str, object]:
    selected_course_ids = selection.selected_course_ids
    artifact_results: dict[str, ArtifactValidationResult] = {}
    failed = False
    for artifact_name, expected_rows in expected_rows_by_artifact.items():
        observed_rows = read_jsonl(bundle_dir / artifact_name)
        expected_course_ids = sorted(
            {_course_id_for_row(row) for row in expected_rows if _course_id_for_row(row) is not None}
        )
        observed_course_ids = sorted(
            {_course_id_for_row(row) for row in observed_rows if _course_id_for_row(row) is not None}
        )
        expected_ids = _expected_ids_for_artifact(artifact_name, expected_rows)
        observed_ids = _expected_ids_for_artifact(artifact_name, observed_rows)
        missing_ids = sorted(set(expected_ids) - set(observed_ids))
        unexpected_ids = sorted(set(observed_ids) - set(expected_ids))
        course_set_ok = observed_course_ids == expected_course_ids
        row_count_ok = len(observed_rows) == len(expected_rows)
        status = "pass" if course_set_ok and row_count_ok and not missing_ids and not unexpected_ids else "fail"
        if status == "fail":
            failed = True
        artifact_results[artifact_name] = ArtifactValidationResult(
            artifact_name=artifact_name,
            expected_row_count=len(expected_rows),
            observed_row_count=len(observed_rows),
            expected_course_ids=expected_course_ids,
            observed_course_ids=observed_course_ids,
            missing_ids=missing_ids,
            unexpected_ids=unexpected_ids,
            status=status,
        )

    expected_yaml_ids = selected_course_ids
    observed_yaml_ids = sorted(path.stem for path in (bundle_dir / "course_yaml").glob("*.yaml"))
    yaml_missing = sorted(set(expected_yaml_ids) - set(observed_yaml_ids))
    yaml_unexpected = sorted(set(observed_yaml_ids) - set(expected_yaml_ids))
    yaml_status = "pass" if not yaml_missing and not yaml_unexpected else "fail"
    if yaml_status == "fail":
        failed = True

    return {
        "bundle_id": selection.bundle_id,
        "source_run_id": selection.source_run_id,
        "export_mode": selection.export_mode,
        "expected_course_ids": selected_course_ids,
        "artifacts": {
            name: asdict(result) for name, result in sorted(artifact_results.items())
        },
        "course_yaml": {
            "expected_course_ids": expected_yaml_ids,
            "observed_course_ids": observed_yaml_ids,
            "missing_ids": yaml_missing,
            "unexpected_ids": yaml_unexpected,
            "status": yaml_status,
        },
        "status": "fail" if failed else "pass",
    }


def _render_bundle_validation_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Bundle Validation",
        "",
        f"- `bundle_id`: `{report['bundle_id']}`",
        f"- `source_run_id`: `{report['source_run_id']}`",
        f"- `export_mode`: `{report['export_mode']}`",
        f"- `status`: `{report['status']}`",
        "",
        "## Expected Courses",
        "",
    ]
    expected_course_ids = report.get("expected_course_ids", [])
    for course_id in expected_course_ids:
        lines.append(f"- `{course_id}`")

    lines.extend(
        [
            "",
            "## Artifact Validation",
            "",
            "| Artifact | Status | Expected Rows | Observed Rows | Expected Courses | Observed Courses |",
            "| --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    artifacts = report.get("artifacts", {})
    for artifact_name, payload in artifacts.items():
        lines.append(
            "| "
            f"`{artifact_name}` | `{payload['status']}` | {payload['expected_row_count']} | {payload['observed_row_count']} | "
            f"`{', '.join(payload['expected_course_ids'])}` | `{', '.join(payload['observed_course_ids'])}` |"
        )
        if payload["missing_ids"]:
            lines.append(f"Missing ids: `{', '.join(payload['missing_ids'][:5])}`")
        if payload["unexpected_ids"]:
            lines.append(f"Unexpected ids: `{', '.join(payload['unexpected_ids'][:5])}`")

    course_yaml = report.get("course_yaml", {})
    lines.extend(
        [
            "",
            "## Course YAML Validation",
            "",
            f"- `status`: `{course_yaml.get('status')}`",
            f"- `expected_course_ids`: `{', '.join(course_yaml.get('expected_course_ids', []))}`",
            f"- `observed_course_ids`: `{', '.join(course_yaml.get('observed_course_ids', []))}`",
        ]
    )
    if course_yaml.get("missing_ids"):
        lines.append(
            f"- `missing_ids`: `{', '.join(course_yaml.get('missing_ids', [])[:5])}`"
        )
    if course_yaml.get("unexpected_ids"):
        lines.append(
            f"- `unexpected_ids`: `{', '.join(course_yaml.get('unexpected_ids', [])[:5])}`"
        )

    return "\n".join(lines) + "\n"


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


@app.command("mk_inspectgion_bundle")
def mk_inspectgion_bundle(
    bundle_id: str = typer.Argument(..., help="Digits-only bundle id such as 0, 1, or 011."),
    export_mode: str = typer.Option(
        "filtered",
        "--export-mode",
        help="Export mode: filtered or full.",
    ),
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
    export_mode_normalized = export_mode.strip().lower()
    if export_mode_normalized not in {"filtered", "full"}:
        raise typer.BadParameter("export_mode must be either 'filtered' or 'full'")
    start = time.perf_counter()
    source_dir = Path(final_dir)
    if not source_dir.exists():
        raise typer.BadParameter(f"final_dir does not exist: {source_dir}")

    bundle_dir = Path(tmp_root) / f"inspectgion_bundl_{bundle_id}"
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    selection = _build_bundle_selection(
        source_dir=source_dir,
        bundle_id=bundle_id,
        export_mode=export_mode_normalized,
    )
    selected_course_ids = set(selection.selected_course_ids)
    missing_course_ids = [
        course_id
        for course_id in sorted(selected_course_ids)
        if not (source_dir / "course_yaml" / f"{course_id}.yaml").exists()
    ]
    if missing_course_ids:
        raise RuntimeError(
            f"missing required selected course outputs in data/final: {', '.join(missing_course_ids)}"
        )

    _bundle_log(
        bundle_dir,
        f"bundle start bundle_id={bundle_id} source_dir={source_dir} export_mode={selection.export_mode}",
    )
    _bundle_log(
        bundle_dir,
        "bundle selection "
        f"selected_course_ids={selection.selected_course_ids} "
        f"selected_question_ids={selection.selected_question_ids} "
        f"selected_row_ids={selection.selected_row_ids}",
    )
    artifact_counts: dict[str, dict[str, int]] = {}
    expected_rows_by_artifact: dict[str, list[dict]] = {}
    for artifact_name in ARTIFACT_FILES:
        source_rows = read_jsonl(source_dir / artifact_name)
        selected_rows = _filter_rows_for_bundle(
            source_rows,
            artifact_name,
            selected_course_ids=set(selection.selected_course_ids),
            selected_question_ids=set(selection.selected_question_ids),
            selected_question_texts=set(selection.selected_question_texts),
            selected_row_ids=set(selection.selected_row_ids),
            selected_train_row_ids=set(selection.selected_train_row_ids),
            selected_cache_keys=set(selection.selected_cache_keys),
        )
        write_jsonl(bundle_dir / artifact_name, selected_rows)
        expected_rows_by_artifact[artifact_name] = selected_rows
        artifact_counts[artifact_name] = {
            "selected_row_count": len(selected_rows),
            "source_row_count": len(source_rows),
        }
        _bundle_log(
            bundle_dir,
            f"artifact filtered name={artifact_name} selected_rows={len(selected_rows)} source_rows={len(source_rows)}",
        )

    selected_yaml_count = 0
    for item in selection.selected_courses:
        source_yaml = source_dir / "course_yaml" / f"{item['course_id']}.yaml"
        target_yaml = bundle_dir / "course_yaml" / f"{item['course_id']}.yaml"
        target_yaml.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_yaml, target_yaml)
        selected_yaml_count += 1

    artifact_counts["course_yaml"] = {
        "selected_file_count": selected_yaml_count,
        "expected_file_count": len(selection.selected_courses),
    }

    source_run_summary = read_yaml(source_dir / "run_summary.yaml")
    if source_run_summary:
        write_yaml(bundle_dir / "source_run_summary.yaml", source_run_summary)

    bundle_summary = rebuild_run_summary(bundle_dir)
    validation_report = _validate_bundle_artifacts(
        bundle_dir=bundle_dir,
        selection=selection,
        expected_rows_by_artifact=expected_rows_by_artifact,
    )
    (bundle_dir / "bundle_validation.json").write_text(
        json.dumps(validation_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (bundle_dir / "bundle_validation.md").write_text(
        _render_bundle_validation_markdown(validation_report),
        encoding="utf-8",
    )
    if validation_report["status"] != "pass":
        raise RuntimeError("bundle validation failed; see bundle_validation.json")

    elapsed = round(time.perf_counter() - start, 3)
    manifest = {
        "bundle_id": selection.bundle_id,
        "bundle_dir": str(bundle_dir),
        "source_final_dir": str(source_dir),
        "bundle_selection": asdict(selection),
        "artifact_counts": artifact_counts,
        "performance_data": {
            "bundle_build_seconds": elapsed,
            "published_run_course_count": source_run_summary.get("course_count"),
            "bundle_course_count": bundle_summary.get("course_count"),
        },
        "log_ownership": {
            "bundle_log_path": str(bundle_dir / "inspectgion_bundle.log"),
            "scope": "bundle_scoped",
        },
    }
    write_yaml(bundle_dir / "pipeline_run_manifest.yaml", manifest)
    _bundle_log(
        bundle_dir,
        f"bundle complete bundle_id={bundle_id} export_mode={selection.export_mode} elapsed_seconds={elapsed}",
    )
    typer.echo(str(bundle_dir))


if __name__ == "__main__":
    app()
