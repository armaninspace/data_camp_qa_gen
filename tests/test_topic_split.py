
from course_pipeline.tasks.normalize import normalize_course_record
from course_pipeline.tasks.extract_topics import extract_atomic_topics_baseline
from course_pipeline.tasks.canonicalize import canonicalize_topics
from course_pipeline.tasks.vet_topics import vet_topics_and_pairs


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


def test_ampersand_heading_is_split_and_singularized() -> None:
    raw = {
        "course_id": "5",
        "title": "Example",
        "syllabus": [{"title": "Dictionaries & Pandas", "summary": "Use the dictionary and pandas DataFrame."}],
    }
    course = normalize_course_record(raw)
    topics = extract_atomic_topics_baseline(course)
    labels = {t.label for t in topics}

    assert "dictionary" in labels
    assert "pandas" in labels
    assert "dictionaries & pandas" not in labels


def test_comma_heading_is_split_and_plural_is_normalized() -> None:
    raw = {
        "course_id": "6",
        "title": "Example",
        "syllabus": [{"title": "Logic, Control Flow, Loops", "summary": "Use logic and loops."}],
    }
    course = normalize_course_record(raw)
    topics = extract_atomic_topics_baseline(course)
    labels = {t.label for t in topics}

    assert "logic" in labels
    assert "control flow" in labels
    assert "loop" in labels
    assert "loops" not in labels


def test_learning_objective_and_clause_fragment_topics_are_rejected() -> None:
    raw = {
        "course_id": "7",
        "title": "Example",
        "syllabus": [
            {"title": "Getting Started in Python", "summary": "Use Python."},
            {"title": "Learn to Manipulate DataFrames", "summary": "Use DataFrames."},
            {"title": "Different Types of Plots", "summary": "Use plots to visualize data."},
            {"title": "WHERE", "summary": "Filter rows with the WHERE clause."},
        ],
    }
    course = normalize_course_record(raw)
    topics = extract_atomic_topics_baseline(course)
    labels = {t.label for t in topics}
    canonical_topics = canonicalize_topics(topics)
    vetted_topics, _ = vet_topics_and_pairs(canonical_topics, [])
    decisions = {item.canonical_label: item.decision for item in vetted_topics}

    assert "getting started in python" not in labels
    assert "learn to manipulate dataframes" not in labels
    assert "different types of plots" not in labels
    assert decisions["where"] == "reject"
