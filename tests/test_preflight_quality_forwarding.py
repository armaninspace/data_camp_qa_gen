from __future__ import annotations

from pathlib import Path

import yaml

from course_pipeline.flows.course_question_pipeline import _process_course
from course_pipeline.io_utils import read_jsonl
from course_pipeline.run_logging import RunLogger


def test_partial_preflight_status_is_persisted_in_normalized_course(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    run_dir = tmp_path / "run"
    input_dir.mkdir()
    (input_dir / "partial.yaml").write_text(
        yaml.safe_dump(
            {
                "course_id": "42",
                "title": "Overview Only Course",
                "overview": "This course covers categorical data and text data.",
                "syllabus": [],
            }
        ),
        encoding="utf-8",
    )

    logger = RunLogger(run_id="run", root_dir=run_dir)
    logger.ensure_files()
    _process_course(
        str(input_dir / "partial.yaml"),
        str(run_dir),
        logger,
        quality_status="partial",
    )

    rows = read_jsonl(run_dir / "normalized_courses.jsonl")
    assert len(rows) == 1
    assert rows[0]["course_id"] == "42"
    assert rows[0]["metadata"]["quality_status"] == "partial"
