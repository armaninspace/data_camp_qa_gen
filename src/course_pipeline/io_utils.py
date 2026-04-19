from __future__ import annotations

from pathlib import Path
import json
from typing import Any

import yaml
from pydantic import BaseModel


def _to_payload(obj: BaseModel | dict[str, Any]) -> dict[str, Any]:
    return obj.model_dump() if hasattr(obj, "model_dump") else obj


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_jsonl(path: str | Path, obj: BaseModel | dict[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _to_payload(obj)
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_yaml(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    payload = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def write_yaml(path: str | Path, obj: BaseModel | dict[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _to_payload(obj)
    with file_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            payload,
            handle,
            allow_unicode=True,
            sort_keys=False,
            width=80,
        )


def course_id_for_row(row: dict[str, Any]) -> str | None:
    if "course_id" in row and row.get("course_id") is not None:
        return str(row["course_id"])
    course = row.get("course")
    if isinstance(course, dict) and course.get("course_id") is not None:
        return str(course["course_id"])
    return None


def upsert_jsonl_rows(
    path: str | Path,
    rows: list[BaseModel | dict[str, Any]],
    course_ids: set[str],
) -> None:
    existing = read_jsonl(path)
    kept = [
        row for row in existing if course_id_for_row(row) not in course_ids
    ]
    kept.extend(_to_payload(row) for row in rows)
    write_jsonl(path, kept)


def normalized_relative_paths(input_root: str | Path) -> list[tuple[str, Path]]:
    root = Path(input_root).resolve()
    paths: list[tuple[str, Path]] = []
    for candidate in root.glob("**/*"):
        if not candidate.is_file():
            continue
        if candidate.suffix.lower() not in {".yaml", ".yml", ".json", ".md"}:
            continue
        relative = candidate.resolve().relative_to(root).as_posix()
        paths.append((relative, candidate.resolve()))
    return sorted(paths, key=lambda item: item[0])
