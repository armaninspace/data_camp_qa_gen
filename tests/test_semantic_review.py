from __future__ import annotations

from pathlib import Path

from course_pipeline.run_logging import RunLogger
from course_pipeline.schemas import NormalizedCourse, SemanticStageResult
from course_pipeline.tasks.semantic_review import run_semantic_review_for_course


class FakeJsonClient:
    def __init__(self, model: str, responses: list[dict]) -> None:
        self.model = model
        self._responses = list(responses)
        self.prompts: list[tuple[str, str]] = []

    def complete_json(self, prompt: str, schema_name: str) -> dict:
        self.prompts.append((schema_name, prompt))
        if not self._responses:
            raise AssertionError(f"no fake response left for schema={schema_name}")
        return self._responses.pop(0)


def _course() -> NormalizedCourse:
    return NormalizedCourse(
        course_id="24374",
        title="Learn to Manipulate DataFrames",
        summary="Use pandas and matplotlib for data analysis.",
        overview="The course teaches pandas, matplotlib, and control flow.",
        chapters=[
            {
                "chapter_index": 1,
                "title": "Getting Started in Python",
                "summary": "Intro material.",
                "source": "syllabus",
                "confidence": 1.0,
            }
        ],
        metadata={"level": "beginner", "subjects": ["python"]},
    )


def _semantic_result() -> SemanticStageResult:
    return SemanticStageResult.model_validate(
        {
            "topics": [
                {
                    "label": "Getting Started in Python",
                    "normalized_label": "getting started in python",
                    "topic_type": "concept",
                    "confidence": 0.42,
                    "course_centrality": 0.2,
                    "source_refs": ["chapter:1"],
                    "rationale": "Appears in a chapter title.",
                },
                {
                    "label": "Pandas",
                    "normalized_label": "pandas",
                    "topic_type": "tool",
                    "confidence": 0.94,
                    "course_centrality": 0.9,
                    "source_refs": ["overview"],
                    "rationale": "Central library.",
                },
            ],
            "correlated_topics": [],
            "topic_questions": [
                {
                    "question_id": "sq_001",
                    "question_text": "What is getting started in python?",
                    "question_family": "what_is",
                    "relevant_topics": ["getting started in python"],
                    "question_scope": "single_topic",
                    "rationale": "Bad wrapper question.",
                }
            ],
            "correlated_topic_questions": [],
            "synthetic_answers": [
                {
                    "question_text": "What is pandas?",
                    "answer_text": "Pandas is a Python library for working with table-shaped data.",
                    "answer_mode": "synthetic_tutor_answer",
                    "difficulty_band": "beginner",
                    "confidence": 0.95,
                    "answer_rationale": "Brief correct answer.",
                    "related_topics": ["pandas"],
                }
            ],
        }
    )


def test_semantic_review_returns_structured_decisions(tmp_path: Path) -> None:
    logger = RunLogger(run_id="run", root_dir=tmp_path)
    logger.ensure_files()
    client = FakeJsonClient(
        "gpt-5.4",
        [
            {
                "decisions": [
                    {
                        "item_type": "topic",
                        "target_id": "getting started in python",
                        "decision": "reject",
                        "rewritten_payload": {},
                        "merged_into": None,
                        "rationale": "Wrapper topic, not learner-facing.",
                    },
                    {
                        "item_type": "question",
                        "target_id": "sq_001",
                        "decision": "reject",
                        "rewritten_payload": {},
                        "merged_into": None,
                        "rationale": "Malformed beginner question.",
                    },
                    {
                        "item_type": "synthetic_answer",
                        "target_id": "What is pandas?",
                        "decision": "keep",
                        "rewritten_payload": {},
                        "merged_into": None,
                        "rationale": "Good beginner answer.",
                    },
                ]
            }
        ],
    )

    result = run_semantic_review_for_course(
        course=_course(),
        semantic_result=_semantic_result(),
        llm_client=client,
        logger=logger,
    )

    assert [item.decision for item in result.decisions] == ["reject", "reject", "keep"]
    llm_logs = (tmp_path / "logs" / "llm_calls.jsonl").read_text(encoding="utf-8")
    assert '"stage": "semantic_review"' in llm_logs
    assert '"prompt_family": "semantic_review"' in llm_logs


def test_semantic_review_prompt_includes_course_yaml_and_bundle_json() -> None:
    client = FakeJsonClient("gpt-5.4", [{"decisions": []}])

    run_semantic_review_for_course(
        course=_course(),
        semantic_result=_semantic_result(),
        llm_client=client,
    )

    schema_name, prompt = client.prompts[0]
    assert schema_name == "semantic_review"
    assert "Getting Started in Python" in prompt
    assert '"normalized_label": "getting started in python"' in prompt
    assert '"question_text": "What is getting started in python?"' in prompt
    assert "{{SEMANTIC_BUNDLE_JSON}}" not in prompt
