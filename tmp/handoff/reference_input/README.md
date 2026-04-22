# Reference Input Data

This directory contains representative raw inputs for the rewrite team.

## Included samples

- `raw_courses/0001-datacamp-introduction-to-r-7630-3dd081a41a56.yaml`
- `raw_courses/0003-datacamp-intermediate-sql-queries-24370-7e985095dd61.yaml`
- `raw_courses/0004-datacamp-intermediate-python-24372-3c1807adc3b4.yaml`

These are not intended to define the new architecture. They are reference
inputs that demonstrate the kind of scraped course YAML the pipeline must
accept.

## Notes

- The filename for course `24370` is historical and does not match the course
  title cleanly. Treat the file contents, not the filename, as authoritative.
- These samples are useful for:
  - normalization tests
  - semantic-stage fixture generation
  - provenance/source-reference handling
  - smoke-run sanity checks
