from __future__ import annotations

from course_pipeline.schemas import TeacherAnswerDraft
from course_pipeline.tasks.build_product_rows import build_cache_rows, build_train_rows


def _teacher_answer(
    *,
    course_id: str,
    question_id: str,
    question_text: str = "What is pandas?",
    weak_grounding: bool = False,
    off_topic: bool = False,
    needs_review: bool = False,
) -> TeacherAnswerDraft:
    return TeacherAnswerDraft.model_validate(
        {
            "course_id": course_id,
            "question_id": question_id,
            "question_text": question_text,
            "provided_context": {
                "course_context_frame": {
                    "course_id": course_id,
                    "course_title": f"Course {course_id}",
                    "learner_level": "beginner",
                    "domain": "data science in python",
                    "primary_tools": ["pandas"],
                    "core_tasks": ["load data"],
                    "scope_bias": ["favor pandas examples"],
                    "answer_style": {
                        "depth": "introductory",
                        "tone": "direct and instructional",
                        "prefer_examples": True,
                        "prefer_definitions": True,
                        "keep_short": True,
                    },
                },
                "question_context_frame": {
                    "question_id": question_id,
                    "course_id": course_id,
                    "question_text": question_text,
                    "question_intent": "definition",
                    "relevant_topics": ["pandas"],
                    "chapter_scope": ["Using pandas"],
                    "expected_answer_shape": ["short definition"],
                    "scope_bias": ["focus on tabular data"],
                    "support_refs": ["summary"],
                },
            },
            "teacher_answer": f"Pandas is explained here for course {course_id}.",
            "course_aligned": True,
            "weak_grounding": weak_grounding,
            "off_topic": off_topic,
            "needs_review": needs_review,
            "model_name": "gpt-5.4",
            "prompt_family": "teacher_answer",
        }
    )


def test_build_train_rows_retains_variants_and_sets_flags() -> None:
    rows = build_train_rows(
        [
            _teacher_answer(course_id="24373", question_id="24373:q:0012"),
        ],
        {
            "24373:q:0012": [
                "What is pandas?",
                "What does pandas do?",
                "What is pandas?",
            ]
        },
    )

    assert len(rows) == 1
    assert rows[0].question_variants == ["What is pandas?", "What does pandas do?"]
    assert rows[0].answer_quality_flags.train_eligible is True
    assert rows[0].answer_quality_flags.cache_eligible is True
    assert rows[0].global_question_signature == "what is pandas"


def test_build_cache_rows_keeps_good_rows_even_when_flagged() -> None:
    train_rows = build_train_rows(
        [
            _teacher_answer(course_id="24373", question_id="24373:q:0012"),
            _teacher_answer(
                course_id="24373",
                question_id="24373:q:0013",
                question_text="What is matplotlib?",
                weak_grounding=True,
            ),
            _teacher_answer(
                course_id="24373",
                question_id="24373:q:0014",
                question_text="What is seaborn?",
                needs_review=True,
            ),
        ]
    )

    cache_rows = build_cache_rows(train_rows)

    assert len(train_rows) == 3
    assert len(cache_rows) == 3
    assert [row.question_text for row in cache_rows] == [
        "What is pandas?",
        "What is matplotlib?",
        "What is seaborn?",
    ]


def test_build_cache_rows_excludes_only_truly_bad_rows() -> None:
    train_rows = build_train_rows(
        [
            _teacher_answer(course_id="24373", question_id="24373:q:0012"),
            _teacher_answer(
                course_id="24373",
                question_id="24373:q:0015",
                question_text="What is off topic?",
                off_topic=True,
            ),
        ]
    )

    cache_rows = build_cache_rows(train_rows)

    assert len(cache_rows) == 1
    assert cache_rows[0].question_text == "What is pandas?"


def test_build_cache_rows_preserves_course_separation_for_same_question() -> None:
    train_rows = build_train_rows(
        [
            _teacher_answer(course_id="24373", question_id="24373:q:0012"),
            _teacher_answer(course_id="24511", question_id="24511:q:0003"),
        ]
    )

    cache_rows = build_cache_rows(train_rows)

    assert len(cache_rows) == 2
    assert cache_rows[0].question_text == cache_rows[1].question_text
    assert cache_rows[0].course_id != cache_rows[1].course_id
    assert cache_rows[0].cache_key != cache_rows[1].cache_key
