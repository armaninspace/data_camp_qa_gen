
.PHONY: install bootstrap test lint prefect_server_start prefect_server_stop prefect_server_status run run_first_1_percent run_percent_slice run_all_5_percent run_all_10_percent run_all_5_percent_with_bundles run_all_10_percent_with_bundles mk_inspectgion_bundle

INPUT_DIR ?= datacamp_data/classcentral-datacamp-yaml
OUTPUT_ROOT ?= data/pipeline_runs
FINAL_DIR ?= data/final
RUN_ID ?= dev_run
SLICE_START ?= 0
SLICE_END ?= 100
BUNDLE_ID ?= 0
TMP_ROOT ?= /tmp
BUNDLE_EVERY ?= 2
BUNDLE_ID_OFFSET ?= 0

install:
	pip install -e .[dev]

bootstrap: install

test:
	pytest

lint:
	ruff check src tests

prefect_server_start:
	./scripts/start_prefect_server.sh

prefect_server_stop:
	./scripts/stop_prefect_server.sh

prefect_server_status:
	./scripts/prefect_server_status.sh

run:
	python -m course_pipeline.cli run --input $(INPUT_DIR) --output $(OUTPUT_ROOT)/$(RUN_ID) --final-dir $(FINAL_DIR) --slice-start $(SLICE_START) --slice-end $(SLICE_END) --publish true

run_first_1_percent:
	./scripts/run_first_1_percent.sh $(RUN_ID)

run_percent_slice:
	./scripts/run_percent_slice.sh $(SLICE_START) $(SLICE_END) $(RUN_ID)

run_all_5_percent:
	./scripts/run_all_5_percent.sh

run_all_10_percent:
	./scripts/run_all_10_percent.sh

run_all_5_percent_with_bundles:
	BUNDLE_EVERY=$(BUNDLE_EVERY) BUNDLE_ID_OFFSET=$(BUNDLE_ID_OFFSET) TMP_ROOT=$(TMP_ROOT) FINAL_DIR=$(FINAL_DIR) ./scripts/run_all_5_percent_with_bundles.sh

run_all_10_percent_with_bundles:
	BUNDLE_EVERY=$(BUNDLE_EVERY) BUNDLE_ID_OFFSET=$(BUNDLE_ID_OFFSET) TMP_ROOT=$(TMP_ROOT) FINAL_DIR=$(FINAL_DIR) ./scripts/run_all_10_percent_with_bundles.sh

mk_inspectgion_bundle:
	./scripts/mk_inspectgion_bundle.sh $(BUNDLE_ID) $(TMP_ROOT)
