from __future__ import annotations

from pathlib import Path

import yaml

from course_pipeline.tasks.normalize import normalize_course_record


REAL_FIXTURE = Path(
    "/code/datacamp_data/classcentral-datacamp-yaml/"
    "0143-datacamp-categorical-data-in-the-tidyverse-24511-904060391f75.yaml"
)


def test_normalize_real_scraped_course() -> None:
    raw = yaml.safe_load(REAL_FIXTURE.read_text(encoding="utf-8"))
    course = normalize_course_record(raw)

    assert course.course_id == "24511"
    assert course.title == "Categorical Data in the Tidyverse"
    assert course.provider == "DataCamp"
    assert course.metadata["level"] == "Intermediate"
    assert len(course.chapters) == 4
    assert course.chapters[0].title == "Introduction to Factor Variables"
