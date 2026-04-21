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
                    "topics": [
                        {
                            "label": "Categorical data",
                            "normalized_label": "categorical data",
                            "topic_type": "concept",
                            "confidence": 0.9,
                            "course_centrality": 0.9,
                            "source_refs": ["overview"],
                            "rationale": "Central concept in the overview.",
                        }
                    ],
                    "correlated_topics": [],
                    "topic_questions": [
                        {
                            "question_id": "sq_001",
                            "question_text": "What is categorical data?",
                            "question_family": "what_is",
                            "relevant_topics": ["categorical data"],
                            "question_scope": "single_topic",
                            "rationale": "Natural entry question.",
                            "source_refs": ["overview"],
                        }
                    ],
                    "correlated_topic_questions": [],
                    "synthetic_answers": [
                        {
                            "question_text": "What is categorical data?",
                            "answer_text": "Categorical data uses labels rather than continuous values.",
                            "answer_mode": "synthetic_tutor_answer",
                            "difficulty_band": "beginner",
                            "confidence": 0.9,
                            "answer_rationale": "Brief definition.",
                            "related_topics": ["categorical data"],
                        }
                    ],
                }
            ),
        ),
        LLMClient(
            api_key=None,
            model="gpt-5.4",
            client=_RepeatingOpenAIClient(
                {
                    "decisions": [
                        {
                            "item_type": "synthetic_answer",
                            "target_id": "What is categorical data?",
                            "decision": "keep",
                            "rewritten_payload": {},
                            "merged_into": None,
                            "rationale": "Good answer.",
                        }
                    ]
                }
            ),
        ),
        quality_status="partial",
    )

    rows = read_jsonl(run_dir / "normalized_courses.jsonl")
    assert len(rows) == 1
    assert rows[0]["course_id"] == "42"
    assert rows[0]["metadata"]["quality_status"] == "partial"
