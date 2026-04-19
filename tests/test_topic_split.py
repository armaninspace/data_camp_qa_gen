
from course_pipeline.tasks.normalize import normalize_course_record
from course_pipeline.tasks.extract_topics import extract_atomic_topics_baseline


def test_coordinated_heading_can_split():
    raw = {
        "course_id": "1",
        "title": "Example",
        "syllabus": [
            {"title": "Categorical and Text Data", "summary": "labels and strings"}
        ],
        "overview": "category labels and strings",
    }
    course = normalize_course_record(raw)
    topics = extract_atomic_topics_baseline(course)
    labels = {t.label for t in topics}
    assert "text data" in labels
    assert "categorical" in labels or "categorical data" in labels


def test_heading_like_case_study_is_rejected() -> None:
    raw = {
        "course_id": "2",
        "title": "Example",
        "syllabus": [
            {
                "title": "Case Study",
                "summary": "Model two series jointly using cointegration models.",
            }
        ],
    }
    course = normalize_course_record(raw)
    topics = extract_atomic_topics_baseline(course)
    labels = {t.label for t in topics}

    assert "case study" not in labels
    assert "cointegration models" in labels


def test_heading_like_some_simple_time_series_is_rejected() -> None:
    raw = {
        "course_id": "3",
        "title": "Example",
        "syllabus": [
            {
                "title": "Some Simple Time Series",
                "summary": "These include white noise and a random walk.",
            }
        ],
    }
    course = normalize_course_record(raw)
    topics = extract_atomic_topics_baseline(course)
    labels = {t.label for t in topics}

    assert "some simple time series" not in labels
    assert "white noise" in labels
    assert "random walk" in labels


def test_heading_like_better_code_with_purrr_is_rejected() -> None:
    raw = {
        "course_id": "4",
        "title": "Example",
        "syllabus": [
            {
                "title": "Better code with purrr",
                "summary": (
                    "We learn compose(), negate(), partial(), and list-columns."
                ),
            }
        ],
    }
    course = normalize_course_record(raw)
    topics = extract_atomic_topics_baseline(course)
    labels = {t.label for t in topics}

    assert "better code with purrr" not in labels
    assert "compose" in labels
    assert "negate" in labels
    assert "partial" in labels
    assert "list-columns" in labels
