# Operations Cheat Sheet

This page is the short operator guide for running corpus slices and creating
inspection bundles.

## Defaults

- Input corpus: `datacamp_data/classcentral-datacamp-yaml`
- Transient run outputs: `data/pipeline_runs/<run_id>`
- Published merged outputs: `data/final`
- Inspection bundle output: `tmp/inspectgion_bundl_<bundle_id>`
- Prefect local API server host/port for script-driven runs: `127.0.0.1:8923`
- Prefect API URL for script-driven runs: `http://127.0.0.1:8923/api`

The pipeline uses deterministic lexicographic ordering of input file paths, so
the same slice boundaries resolve reproducibly against the same corpus snapshot.

## Convenience Scripts

### Run the first 1%

```sh
./scripts/run_first_1_percent.sh
```

Custom run id:

```sh
./scripts/run_first_1_percent.sh smoke_1_percent
```

### Run any slice by percent

```sh
./scripts/run_percent_slice.sh <slice_start> <slice_end> [run_id]
```

Examples:

```sh
./scripts/run_percent_slice.sh 0 5 slice_000_005
./scripts/run_percent_slice.sh 5 10 slice_005_010
./scripts/run_percent_slice.sh 90 100 slice_090_100
```

### Run the full 5% sweep

```sh
./scripts/run_all_5_percent.sh
```

### Run the full 10% sweep

```sh
./scripts/run_all_10_percent.sh
```

### Run the full 5% sweep with bundle checkpoints

```sh
./scripts/run_all_5_percent_with_bundles.sh
```

Default behavior:

- creates a bundle every 2 slices
- bundle ids are digits only and look like `2`, `4`, ...

### Run the full 10% sweep with bundle checkpoints

```sh
./scripts/run_all_10_percent_with_bundles.sh
```

Default behavior:

- creates a bundle after every slice
- bundle ids are digits only and look like `101`, `102`, ...

### Create an inspection bundle

```sh
./scripts/mk_inspectgion_bundle.sh <bundle_id>
```

Examples:

```sh
./scripts/mk_inspectgion_bundle.sh 0
./scripts/mk_inspectgion_bundle.sh 011
./scripts/mk_inspectgion_bundle.sh 7 tmp
```

### Start, inspect, or stop the fixed-port Prefect server

```sh
./scripts/start_prefect_server.sh
./scripts/prefect_server_status.sh
./scripts/stop_prefect_server.sh
```

## Direct CLI Equivalents

### First 1%

```sh
python -m course_pipeline.cli run \
  --input datacamp_data/classcentral-datacamp-yaml \
  --output data/pipeline_runs/first_1_percent \
  --final-dir data/final \
  --slice-start 0 \
  --slice-end 1 \
  --publish
```

### Arbitrary slice

```sh
python -m course_pipeline.cli run \
  --input datacamp_data/classcentral-datacamp-yaml \
  --output data/pipeline_runs/<run_id> \
  --final-dir data/final \
  --slice-start <start_percent> \
  --slice-end <end_percent> \
  --publish
```

### Inspection bundle

```sh
python -m course_pipeline.cli mk_inspectgion_bundle <bundle_id> \
  --final-dir data/final \
  --tmp-root tmp
```

## Make Targets

### First 1%

```sh
make run_first_1_percent
make run_first_1_percent RUN_ID=smoke_1_percent
```

### Any slice

```sh
make run_percent_slice SLICE_START=25 SLICE_END=30 RUN_ID=slice_025_030
```

### Full sweeps

```sh
make run_all_5_percent
make run_all_10_percent
make run_all_5_percent_with_bundles BUNDLE_EVERY=2 BUNDLE_ID_OFFSET=0
make run_all_10_percent_with_bundles BUNDLE_EVERY=1 BUNDLE_ID_OFFSET=100
```

### Inspection bundle

```sh
make mk_inspectgion_bundle BUNDLE_ID=0
make mk_inspectgion_bundle BUNDLE_ID=011
```

### Prefect server lifecycle

```sh
make prefect_server_start
make prefect_server_status
make prefect_server_stop
```

### Override directories

```sh
make run_percent_slice \
  INPUT_DIR=datacamp_data/classcentral-datacamp-yaml \
  OUTPUT_ROOT=/tmp/pipeline_runs \
  FINAL_DIR=/tmp/final \
  SLICE_START=0 \
  SLICE_END=10 \
  RUN_ID=slice_000_010
```

## 5% Run Plan

Use these 20 deterministic slices:

```text
00-05
05-10
10-15
15-20
20-25
25-30
30-35
35-40
40-45
45-50
50-55
55-60
60-65
65-70
70-75
75-80
80-85
85-90
90-95
95-100
```

Suggested run ids:

```text
slice_000_005
slice_005_010
slice_010_015
slice_015_020
slice_020_025
slice_025_030
slice_030_035
slice_035_040
slice_040_045
slice_045_050
slice_050_055
slice_055_060
slice_060_065
slice_065_070
slice_070_075
slice_075_080
slice_080_085
slice_085_090
slice_090_095
slice_095_100
```

Example command pattern:

```sh
./scripts/run_percent_slice.sh 25 30 slice_025_030
make run_percent_slice SLICE_START=25 SLICE_END=30 RUN_ID=slice_025_030
```

Suggested operating pattern:

1. Start with `./scripts/run_first_1_percent.sh` as a smoke test.
2. Run the 5% slices in ascending order.
3. Inspect `data/final/run_summary.yaml` after each successful publish.
4. Create an inspection bundle periodically, for example after every 2 to 4
   slices.

## 10% Run Plan

Use these 10 deterministic slices:

```text
00-10
10-20
20-30
30-40
40-50
50-60
60-70
70-80
80-90
90-100
```

Suggested run ids:

```text
slice_000_010
slice_010_020
slice_020_030
slice_030_040
slice_040_050
slice_050_060
slice_060_070
slice_070_080
slice_080_090
slice_090_100
```

Example command pattern:

```sh
./scripts/run_percent_slice.sh 40 50 slice_040_050
make run_percent_slice SLICE_START=40 SLICE_END=50 RUN_ID=slice_040_050
```

Suggested operating pattern:

1. Use 10% slices when you want fewer, longer runs.
2. Create an inspection bundle after each 10% slice if you want stable
   checkpoints.
3. If one 10% slice looks suspicious, rerun that exact band or switch to 5%
   slices inside that range for tighter debugging.

## Inspection Bundle Cheatsheet

The inspection bundle always reads from `data/final`, not from a transient run
directory.

For a given numeric `bundle_id`, the command selects 4 published courses at
random from `data/final/course_yaml`, using the bundle id as the random seed.
That means:

- different bundle ids usually produce different 4-course bundles
- rerunning the same bundle id against the same published outputs is reproducible

Rules that matter operationally:

- bundle id must be digits only
- bundle creation fails if fewer than 4 published course bundles exist in
  `data/final/course_yaml`
- the output directory is replaced on each run for the same bundle id

Useful commands:

```sh
./scripts/mk_inspectgion_bundle.sh 0
./scripts/mk_inspectgion_bundle.sh 1
./scripts/mk_inspectgion_bundle.sh 011
make mk_inspectgion_bundle BUNDLE_ID=0
make mk_inspectgion_bundle BUNDLE_ID=011
```

## How To Use Them

### Smallest safe path

1. Run a smoke test:
   ```sh
   ./scripts/run_first_1_percent.sh
   ```
2. Check the merged summary:
   ```sh
   sed -n '1,200p' data/final/run_summary.yaml
   ```
3. Build an inspection bundle:
   ```sh
   ./scripts/mk_inspectgion_bundle.sh 0
   ```

These repo scripts now ensure a dedicated Prefect server is available at
`127.0.0.1:8923` before launching pipeline work. They no longer rely on the
random-port ephemeral server path.

### If you want manual control

1. Run one band at a time:
   ```sh
   ./scripts/run_percent_slice.sh 0 5 slice_000_005
   ./scripts/run_percent_slice.sh 5 10 slice_005_010
   ```
2. Inspect `data/final` after each publish.
3. Create a new bundle id whenever you want a fresh inspection snapshot.

### If you want the whole schedule

1. Full 5% rollout:
   ```sh
   ./scripts/run_all_5_percent.sh
   ```
2. Full 10% rollout:
   ```sh
   ./scripts/run_all_10_percent.sh
   ```

These batch scripts stop on the first failing slice because they run with
`set -eu`.

### If you want the whole schedule plus automatic bundle checkpoints

1. 5% rollout with a bundle every 2 slices:
   ```sh
   ./scripts/run_all_5_percent_with_bundles.sh
   ```
2. 10% rollout with a bundle after every slice:
   ```sh
   ./scripts/run_all_10_percent_with_bundles.sh
   ```
3. To change the cadence:
   ```sh
   BUNDLE_EVERY=3 BUNDLE_ID_OFFSET=200 ./scripts/run_all_5_percent_with_bundles.sh
   BUNDLE_EVERY=2 BUNDLE_ID_OFFSET=300 ./scripts/run_all_10_percent_with_bundles.sh
   ```

Equivalent `make` usage:

```sh
make run_all_5_percent_with_bundles BUNDLE_EVERY=3 BUNDLE_ID_OFFSET=200
make run_all_10_percent_with_bundles BUNDLE_EVERY=2 BUNDLE_ID_OFFSET=300
```

What to inspect after bundle creation:

- `tmp/inspectgion_bundl_<bundle_id>/pipeline_run_manifest.yaml`
- `tmp/inspectgion_bundl_<bundle_id>/inspectgion_bundle.log`
- `tmp/inspectgion_bundl_<bundle_id>/course_yaml/`

## Environment Overrides

The convenience scripts support these environment overrides:

- `INPUT_DIR`
- `OUTPUT_ROOT`
- `FINAL_DIR`
- `PREFECT_SERVER_API_HOST`
- `PREFECT_SERVER_API_PORT`

Example:

```sh
FINAL_DIR=/tmp/final_snapshot \
OUTPUT_ROOT=/tmp/pipeline_runs \
./scripts/run_percent_slice.sh 0 10 slice_000_010
```

Port override example:

```sh
PREFECT_SERVER_API_PORT=8930 ./scripts/run_first_1_percent.sh
```
