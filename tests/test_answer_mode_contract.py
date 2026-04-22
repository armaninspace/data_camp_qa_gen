from __future__ import annotations

import pytest
from pydantic import ValidationError

from course_pipeline.schemas import AnswerRecord


@pytest.mark.parametrize("legacy_mode", ["grounded_course_answer", "blended_answer"])
def test_answer_record_rejects_legacy_answer_modes(legacy_mode: str) -> None:
    with pytest.raises(ValidationError, match="synthetic_tutor_answer"):
        AnswerRecord(
            question_id="sq_001",
            question_text="What is pandas?",
            answer_text="Pandas is a Python library.",
            answer_mode=legacy_mode,
        )
