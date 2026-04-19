
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
