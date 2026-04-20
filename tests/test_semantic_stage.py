from __future__ import annotations

from pathlib import Path

from course_pipeline.run_logging import RunLogger
from course_pipeline.schemas import NormalizedCourse
from course_pipeline.tasks.semantic_stage import run_semantic_stage_for_course


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
        course_id="24372",
        title="Intermediate Python",
        summary="Learn pandas, matplotlib, and control flow.",
        overview=(
            "This course teaches learners how to work with pandas and matplotlib. "
            "It also covers logic, control flow, filtering, and loops."
        ),
        chapters=[
            {
                "chapter_index": 1,
                "title": "Dictionaries & Pandas",
                "summary": "Use dictionaries and pandas together.",
                "source": "syllabus",
                "confidence": 1.0,
            },
            {
                "chapter_index": 2,
                "title": "Logic, Control Flow and Filtering",
                "summary": "Use logic and filtering with loops.",
                "source": "syllabus",
                "confidence": 1.0,
            },
        ],
        metadata={"level": "beginner", "subjects": ["python"]},
    )


def test_semantic_stage_returns_structured_bundle(tmp_path: Path) -> None:
    logger = RunLogger(run_id="run", root_dir=tmp_path)
    logger.ensure_files()
    client = FakeJsonClient(
        "gpt-5.4",
        [
            {
                "topics": [
                    {
                        "label": "Pandas",
                        "normalized_label": "pandas",
                        "topic_type": "tool",
                        "confidence": 0.96,
                        "course_centrality": 0.93,
                        "source_refs": ["chapter:1", "overview"],
                        "rationale": "Repeated as a central library.",
                        "aliases": ["pandas library"],
                    },
                    {
                        "label": "Control Flow",
                        "normalized_label": "control flow",
                        "topic_type": "concept",
                        "confidence": 0.91,
                        "course_centrality": 0.82,
                        "source_refs": ["chapter:2"],
                        "rationale": "Explicit chapter topic.",
                    },
                ],
                "correlated_topics": [
                    {
                        "topics": ["pandas", "matplotlib"],
                        "relationship_type": "used_together",
                        "strength": 0.84,
                        "rationale": "Common plotting workflow.",
                    }
                ],
                "topic_questions": [
                    {
                        "question_id": "sq_001",
                        "question_text": "What is pandas?",
                        "question_family": "what_is",
                        "relevant_topics": ["pandas"],
                        "question_scope": "single_topic",
                        "rationale": "Natural beginner entry question.",
                        "source_refs": ["chapter:1"],
                    }
                ],
                "correlated_topic_questions": [
                    {
                        "question_id": "cq_001",
                        "question_text": "How are pandas and matplotlib related?",
                        "question_family": "how_are_x_and_y_related",
                        "relevant_topics": ["pandas", "matplotlib"],
                        "question_scope": "correlated_topics",
                        "rationale": "Natural workflow bridge question.",
                        "source_refs": ["overview"],
                    }
                ],
                "synthetic_answers": [
                    {
                        "question_text": "What is pandas?",
                        "answer_text": "Pandas is a Python library for working with tabular data.",
                        "answer_mode": "synthetic_tutor_answer",
                        "difficulty_band": "beginner",
                        "confidence": 0.97,
                        "answer_rationale": "Brief beginner definition.",
                        "related_topics": ["pandas"],
                    }
                ],
            }
        ],
    )

    result = run_semantic_stage_for_course(course=_course(), llm_client=client, logger=logger)

    assert result.topics[0].normalized_label == "pandas"
    assert result.correlated_topics[0].topics == ["pandas", "matplotlib"]
    assert result.topic_questions[0].question_family == "what_is"
    assert result.correlated_topic_questions[0].question_scope == "correlated_topics"
    assert result.synthetic_answers[0].answer_mode == "synthetic_tutor_answer"

    llm_logs = (tmp_path / "logs" / "llm_calls.jsonl").read_text(encoding="utf-8")
    assert '"stage": "semantic_stage"' in llm_logs
    assert '"prompt_family": "semantic_stage"' in llm_logs


def test_semantic_stage_prompt_uses_whole_normalized_course_yaml() -> None:
    client = FakeJsonClient(
        "gpt-5.4",
        [
            {
                "topics": [],
                "correlated_topics": [],
                "topic_questions": [],
                "correlated_topic_questions": [],
                "synthetic_answers": [],
            }
        ],
    )

    run_semantic_stage_for_course(course=_course(), llm_client=client)

    schema_name, prompt = client.prompts[0]
    assert schema_name == "semantic_stage"
    assert "course_id: '24372'" in prompt or "course_id: \"24372\"" in prompt
    assert "Dictionaries & Pandas" in prompt
    assert "Logic, Control Flow and Filtering" in prompt
    assert "This course teaches learners how to work with pandas and matplotlib." in prompt
    assert "{{NORMALIZED_COURSE_YAML}}" not in prompt
