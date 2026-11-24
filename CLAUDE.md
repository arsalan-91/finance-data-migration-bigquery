# Finance Data Migration to BigQuery

Project instructions for AI coding assistants working on this repository.

## The project
ELT pipeline moving synthetic SAP-style finance data (COBK headers, COEP line items)
from PostgreSQL into BigQuery, transformed and tested with dbt, orchestrated by Airflow,
with quarantine, reconciliation and failure alerts. No real company data is ever used.

## Phases
- Phase 0: repo, CLAUDE.md, .gitignore, venv, src/generator/generate_data.py, sample_data, README
- Phase 1: PostgreSQL 16 in Docker (127.0.0.1 only), GCP project + budget alert, ADC, BigQuery datasets
- Phase 2: src/load/extract_load.py (watermark, load jobs), run tracker, idempotency test, pytest
- Phase 3: dbt: sources + freshness, validation/quarantine, staging, intermediate, marts, tests
- Phase 4: Airflow DAG: load -> dbt build -> reconcile, retries, failure alerts
- Phase 5: GitHub Actions CI (ruff, pytest, dbt build on dev), runbook, final README
- Phase 6 (optional): CDC with Debezium + Redpanda from PostgreSQL

Current phase: Phase 1

## Data model
- BigQuery datasets (US): fin_raw, fin_staging, fin_intermediate, fin_marts, fin_quarantine, fin_ops
- fin_ops.pipeline_runs: run_id, pipeline, started_at, finished_at, rows_extracted, rows_loaded, status, error_message
- Quarantine rules (rejection_reason): missing_key, line_without_header, unbalanced_document,
  zero_amount, unknown_cost_center, invalid_posting_date
- Golden rule: raw rows per run = staging + quarantine
- Loads are idempotent (MERGE on key). Running a load twice must not duplicate rows.
- PostgreSQL raw source tables have no PRIMARY KEY and no NOT NULL constraints: COPY reads
  empty CSV fields as NULL, and missing_key rows must reach fin_raw so dbt can detect them.

## Conventions
- dbt: stg_<source>__<entity>, int_<entity>__<verb>, fct_<subject>_<grain>, dim_<entity>
- Columns snake_case; timestamps end with _at, dates with _date, flags start with is_; technical columns start with _
- Python: ruff, type hints, logging instead of print
- Commits: Conventional Commits, e.g. feat(generator): add COBK/COEP generator

## Security rules
- Never read, print or commit .env files, keys or credentials.
- Google Cloud auth uses Application Default Credentials (gcloud auth application-default login). No key files.
- Docker ports bind to 127.0.0.1 only. Change all default passwords.
- Run git status before every commit: data/, .venv/ and secrets must not appear.
- BigQuery: load jobs only (no streaming inserts), partitioned tables, check bytes processed before running.