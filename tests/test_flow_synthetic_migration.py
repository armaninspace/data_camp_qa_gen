from __future__ import annotations

from pathlib import Path

import yaml

from course_pipeline.flows.course_question_pipeline import course_question_pipeline_flow
from course_pipeline.io_utils import read_jsonl, read_yaml
from course_pipeline.llm import LLMClient


class FakeJsonClient:
    def __init__(self, responses: list[dict]) -> None:
        self._responses = list(responses)

    def responses_parse(self, prompt: str, schema_name: str) -> dict:
        if not self._responses:
            raise AssertionError(f"no fake response left for schema={schema_name}")
        return self._responses.pop(0)


class FakeResponsesAPI:
    def __init__(self, responses: list[dict]) -> None:
        self._client = FakeJsonClient(responses)

    def create(self, *, model: str, input: str, text: dict, metadata: dict) -> object:
        payload = self._client.responses_parse(input, str(metadata["schema_name"]))

        class _Response:
            def __init__(self, data: dict) -> None:
                import json

                self.output_text = json.dumps(data)

        return _Response(payload)


class FakeOpenAIClient:
    def __init__(self, model: str, responses: list[dict]) -> None:
        self.model = model
        self.responses = FakeResponsesAPI(responses)


class FailingResponsesAPI:
    def create(self, *, model: str, input: str, text: dict, metadata: dict) -> object:
        raise RuntimeError(f"synthetic stage failed for {metadata['schema_name']}")


class FailingOpenAIClient:
    def __init__(self, model: str = "gpt-5.4") -> None:
        self.model = model
        self.responses = FailingResponsesAPI()


def _write_course(path: Path) -> None:
    payload = {
        "course_id": "24372",
        "title": "Intermediate Python",
        "provider": "DataCamp",
        "summary": "Learn ARIMA forecasting and time-series basics in Python.",
        "overview": (
            "This course teaches ARIMA and forecasting workflows. "
            "You will learn when to use ARIMA and how forecasting works."
        ),
        "syllabus": [
            {
                "title": "ARIMA",
                "summary": "Learn the ARIMA model for forecasting time series data.",
            }
        ],
        "details": {"level": "Beginner", "duration_hours": "4 hours"},
        "subjects": ["Python", "Time Series"],
        "source_url": "https://example.com/course/intermediate-python-24372",
        "final_url": "https://example.com/course/intermediate-python-24372",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _write_broken_course(path: Path) -> None:
    payload = {
        "course_id": "99999",
        "overview": "",
        "syllabus": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_main_flow_publishes_synthetic_answers(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    run_dir = tmp_path / "run"
    final_dir = tmp_path / "final"
    _write_course(input_dir / "course.yaml")
    _write_broken_course(input_dir / "broken.yaml")

    semantic_client = LLMClient(
        api_key=None,
        model="gpt-5.4",
        client=FakeOpenAIClient(
            "gpt-5.4",
            [
                {
                    "topics": [
                        {
                            "label": "ARIMA",
                            "normalized_label": "arima",
                            "topic_type": "concept",
                            "confidence": 0.94,
                            "course_centrality": 0.95,
                            "source_refs": ["overview", "chapter:1"],
                            "rationale": "Repeated central concept.",
                        }
                    ],
                    "correlated_topics": [],
                    "topic_questions": [
                        {
                            "question_id": "sq_001",
                            "question_text": "What is ARIMA?",
                            "question_family": "what_is",
                            "relevant_topics": ["arima"],
                            "question_scope": "single_topic",
                            "rationale": "Natural entry question.",
                        }
                    ],
                    "correlated_topic_questions": [],
                    "synthetic_answers": [
                        {
                            "question_text": "What is ARIMA?",
                            "answer_text": "ARIMA is a forecasting model that combines autoregression, differencing, and moving averages.",
                            "answer_mode": "synthetic_tutor_answer",
                            "difficulty_band": "beginner",
                            "confidence": 0.94,
                            "answer_rationale": "Brief beginner definition.",
                        }
                    ],
                }
            ],
        ),
    )
    review_client = LLMClient(
        api_key=None,
        model="gpt-5.4",
        client=FakeOpenAIClient(
            "gpt-5.4",
            [
                {
                    "decisions": [
                        {
                            "item_type": "synthetic_answer",
                            "target_id": "What is ARIMA?",
                            "decision": "keep",
                            "rewritten_payload": {},
                            "merged_into": None,
                            "rationale": "Good answer.",
                        }
                    ]
                }
            ],
        ),
    )

    result = course_question_pipeline_flow(
        input_dir=str(input_dir),
        output_dir=str(run_dir),
        final_dir=str(final_dir),
        publish=True,
        semantic_client=semantic_client,
        review_client=review_client,
    )

    assert result["run_summary"]["course_count"] == 1
    answers = read_jsonl(run_dir / "answers.jsonl")
    assert len(answers) == 1
    assert answers[0]["answer_mode"] == "synthetic_tutor_answer"
    assert answers[0]["validation_status"] == "accept"
    assert "forecasting model" in answers[0]["answer_text"]

    bundle = read_yaml(final_dir / "course_yaml" / "24372.yaml")
    assert bundle["answers"][0]["answer_mode"] == "synthetic_tutor_answer"
    assert bundle["synthetic_answers"][0]["answer_mode"] == "synthetic_tutor_answer"
    assert bundle["final_rows"][0]["question_answer"] == answers[0]["answer_text"]


def test_main_flow_fails_closed_without_grounded_fallback(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    run_dir = tmp_path / "run"
    _write_course(input_dir / "course.yaml")

    try:
        course_question_pipeline_flow(
            input_dir=str(input_dir),
            output_dir=str(run_dir),
            publish=False,
            semantic_client=LLMClient(
                api_key=None, model="gpt-5.4", client=FailingOpenAIClient()
            ),
            review_client=None,
        )
    except RuntimeError as exc:
        assert "semantic_stage" in str(exc)
    else:
        raise AssertionError("expected semantic-stage failure to stop the run")
