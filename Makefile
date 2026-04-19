
.PHONY: install test lint run

install:
	pip install -e .[dev]

test:
	pytest

lint:
	ruff check src tests

run:
	python -m course_pipeline.cli run --input data/scraped --output data/pipeline_runs/dev_run
