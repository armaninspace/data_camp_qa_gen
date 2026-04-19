from __future__ import annotations

from pathlib import Path

from course_pipeline.flows.course_question_pipeline import _slice_indexes, load_course_paths


def test_slice_indexes_for_five_percent_of_twenty() -> None:
    assert _slice_indexes(20, 0.0, 5.0) == (0, 1)


def test_load_course_paths_uses_normalized_lexicographic_order(tmp_path: Path) -> None:
    root = tmp_path / "input"
    (root / "b").mkdir(parents=True)
    (root / "a").mkdir(parents=True)
    (root / "b" / "02.yaml").write_text("title: second\n", encoding="utf-8")
    (root / "a" / "01.yaml").write_text("title: first\n", encoding="utf-8")
    (root / "b" / "03.yaml").write_text("title: third\n", encoding="utf-8")

    selected = load_course_paths.fn(str(root), 0.0, 50.0)

    assert [item.relative_path for item in selected] == ["a/01.yaml", "b/02.yaml"]
