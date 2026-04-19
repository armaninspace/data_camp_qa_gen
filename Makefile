
.PHONY: install test lint run mk_inspectgion_bundle

install:
	pip install -e .[dev]

test:
	pytest

lint:
	ruff check src tests

run:
	python -m course_pipeline.cli run --input data/scraped --output data/pipeline_runs/dev_run

mk_inspectgion_bundle:
	python -m course_pipeline.cli mk_inspectgion_bundle 0
