from __future__ import annotations

from pathlib import Path

from course_pipeline.llm import JSONCompletionResult, LLMUsage
from course_pipeline.run_logging import RunLogger
from course_pipeline.schemas import CourseContextFrame, QuestionContextFrame
from course_pipeline.tasks.generate_teacher_answers import (
    generate_teacher_answer,
)


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

    def complete_json_result(self, prompt: str, schema_name: str) -> JSONCompletionResult:
        return JSONCompletionResult(
            payload=self.complete_json(prompt, schema_name),
            response_id="resp_teacher",
            actual_model=f"{self.model}-snapshot",
            usage=LLMUsage(tokens_in=44, tokens_out=18, cached_tokens_in=7),
        )


def _course_context(course_id: str, title: str, domain: str) -> CourseContextFrame:
    return CourseContextFrame.model_validate(
        {
            "course_id": course_id,
            "course_title": title,
            "learner_level": "beginner",
            "domain": domain,
            "primary_tools": ["pandas"],
            "core_tasks": ["load data", "inspect tabular data"],
            "scope_bias": ["favor pandas examples", f"answer within {domain}"],
            "answer_style": {
                "depth": "introductory",
                "tone": "direct and instructional",
                "prefer_examples": True,
                "prefer_definitions": True,
                "keep_short": True,
            },
        }
    )


def _question_context(course_id: str, question_id: str) -> QuestionContextFrame:
    return QuestionContextFrame.model_validate(
        {
            "question_id": question_id,
            "course_id": course_id,
            "question_text": "What is pandas?",
            "question_intent": "definition",
            "relevant_topics": ["pandas", "tabular data"],
            "chapter_scope": ["Using pandas"],
            "expected_answer_shape": [
                "short definition",
                "why it matters in this course",
                "one simple example",
            ],
            "scope_bias": ["focus on tabular data"],
            "support_refs": ["summary", "chapter_2"],
        }
    )


def test_generate_teacher_answer_uses_provided_context_in_prompt(tmp_path: Path) -> None:
    logger = RunLogger(run_id="run", root_dir=tmp_path)
    logger.ensure_files()
    client = FakeJsonClient(
        "gpt-5.4",
        [
            {
                "teacher_answer": "Pandas is a Python library for working with tabular data in this course.",
                "course_aligned": True,
                "weak_grounding": False,
                "off_topic": False,
                "needs_review": False,
            }
        ],
    )

    result = generate_teacher_answer(
        course_context_frame=_course_context(
            "24373", "Intro to Data Science in Python", "data science in python"
        ),
        question_context_frame=_question_context("24373", "24373:q:0012"),
        llm_client=client,
        logger=logger,
    )

    assert result.course_id == "24373"
    assert result.prompt_family == "teacher_answer"
    assert result.course_aligned is True

    schema_name, prompt = client.prompts[0]
    assert schema_name == "teacher_answer"
    assert '"course_context_frame"' in prompt
    assert '"question_context_frame"' in prompt
    assert '"course_id": "24373"' in prompt
    assert '"question_text": "What is pandas?"' in prompt
    llm_logs = (tmp_path / "logs" / "llm_calls.jsonl").read_text(encoding="utf-8")
    assert '"provider_request_id": "resp_teacher"' in llm_logs
    assert '"tokens_in": 44' in llm_logs
    assert '"tokens_out": 18' in llm_logs


def test_generate_teacher_answer_can_differ_for_same_question_across_courses() -> None:
    python_client = FakeJsonClient(
        "gpt-5.4",
        [
            {
                "teacher_answer": "Pandas is a Python library for tabular data analysis in this course.",
                "course_aligned": True,
                "weak_grounding": False,
                "off_topic": False,
                "needs_review": False,
            }
        ],
    )
    r_client = FakeJsonClient(
        "gpt-5.4",
        [
            {
                "teacher_answer": "In this course, pandas is discussed as part of Python-based tabular workflows rather than R tooling.",
                "course_aligned": True,
                "weak_grounding": False,
                "off_topic": False,
                "needs_review": False,
            }
        ],
    )

    python_answer = generate_teacher_answer(
        course_context_frame=_course_context(
            "24373", "Intro to Data Science in Python", "data science in python"
        ),
        question_context_frame=_question_context("24373", "24373:q:0012"),
        llm_client=python_client,
    )
    r_answer = generate_teacher_answer(
        course_context_frame=_course_context(
            "24511", "Data Skills in R", "data analysis in r"
        ),
        question_context_frame=_question_context("24511", "24511:q:0003"),
        llm_client=r_client,
    )

    assert python_answer.question_text == r_answer.question_text
    assert python_answer.course_id != r_answer.course_id
    assert python_answer.teacher_answer != r_answer.teacher_answer
