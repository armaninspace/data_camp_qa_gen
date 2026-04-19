from __future__ import annotations

from pathlib import Path

import yaml

from course_pipeline.flows.course_question_pipeline import _process_course
from course_pipeline.io_utils import read_jsonl
from course_pipeline.llm import LLMClient
from course_pipeline.run_logging import RunLogger


class _RepeatingResponsesAPI:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def create(self, *, model: str, input: str, text: dict, metadata: dict) -> object:
        class _Response:
            def __init__(self, data: dict) -> None:
                import json

                self.output_text = json.dumps(data)

        return _Response(self.payload)


class _RepeatingOpenAIClient:
    def __init__(self, payload: dict) -> None:
        self.responses = _RepeatingResponsesAPI(payload)


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
        LLMClient(
            api_key=None,
            model="gpt-5.4",
            client=_RepeatingOpenAIClient(
                {
                    "answer_text": "Categorical data uses labels rather than continuous values.",
                    "target_verbosity": "brief",
                    "self_assessed_confidence": 0.9,
                    "notable_risks": [],
                }
            ),
        ),
        LLMClient(
            api_key=None,
            model="gpt-5.4",
            client=_RepeatingOpenAIClient(
                {
                    "decision": "accept",
                    "correctness": 0.95,
                    "sufficiency": 0.9,
                    "brevity": 0.9,
                    "pedagogical_fit": 0.9,
                    "difficulty_alignment": 0.9,
                    "clarity": 0.9,
                    "contradiction_risk": 0.01,
                    "scope_drift": 0.01,
                    "rewritten_answer_text": None,
                    "reject_reasons": [],
                }
            ),
        ),
        quality_status="partial",
    )

    rows = read_jsonl(run_dir / "normalized_courses.jsonl")
    assert len(rows) == 1
    assert rows[0]["course_id"] == "42"
    assert rows[0]["metadata"]["quality_status"] == "partial"
