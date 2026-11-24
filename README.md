# Finance Data Migration to BigQuery

An ELT pipeline that moves synthetic SAP-style controlling (CO) documents from
PostgreSQL into Google BigQuery, transforms and tests them with dbt, and
orchestrates the flow with Airflow. It includes quarantine of invalid rows,
row-count reconciliation and failure alerts.

> All data in this repository is synthetic. No real company data is used.

## Status

| Phase | Scope | Status |
|---|---|---|
| 0 | Repository, synthetic data generator, sample data | Done |
| 1 | PostgreSQL 16 in Docker, GCP project, BigQuery datasets | Planned |
| 2 | Incremental extract & load (watermark, load jobs, run tracker) | Planned |
| 3 | dbt: sources, quarantine, staging, intermediate, marts, tests | Planned |
| 4 | Airflow DAG: load → dbt build → reconcile, alerts | Planned |
| 5 | GitHub Actions CI, runbook | Planned |
| 6 | Optional: CDC with Debezium + Redpanda | Optional |

## Architecture (target)

```
generator ──CSV──▶ PostgreSQL ──extract/load──▶ BigQuery fin_raw
                                                   │
                                            dbt build
                                                   │
                     ┌──────────────┬──────────────┼──────────────┐
                     ▼              ▼              ▼              ▼
               fin_staging   fin_intermediate   fin_marts   fin_quarantine
                                                   │
                                   reconciliation ─┴─▶ fin_ops.pipeline_runs
```

Golden rule: for every run, `raw rows = staging rows + quarantine rows`.

## Source data model

The generator produces SAP-style manual cost repostings (business transaction `RKU1`).
Column names follow SAP technical field names in lowercase; dbt staging renames them.

| File | SAP table | Content |
|---|---|---|
| `csks.csv` | CSKS | Cost center master data |
| `cobk.csv` | COBK | CO document headers |
| `coep.csv` | COEP | CO document line items |

Key fields: `kokrs` controlling area, `belnr` document number, `gjahr` fiscal year,
`buzei` line item, `budat` posting date, `perio` period, `objnr` object number
(`KS` + controlling area + cost center), `kstar` cost element, `wkgbtr` amount,
`twaer` currency (SAR), `beknz` debit/credit indicator (`S`/`H`).

Every valid document is balanced: the sum of `wkgbtr` per document is `0.00`.

### Injected data quality errors

A configurable share of documents receives exactly one error, matching the
quarantine rules that dbt will enforce:

| `rejection_reason` | How the error is produced |
|---|---|
| `missing_key` | `buzei` is empty on one line item |
| `line_without_header` | The COBK header is dropped; line items remain |
| `unbalanced_document` | One line amount is increased by 10.00 |
| `zero_amount` | An extra line item with amount 0.00 is added |
| `unknown_cost_center` | A line posts to `CC9999`, which is not in CSKS |
| `invalid_posting_date` | `budat` falls outside fiscal year `gjahr` |

## Getting started

Requirements: Python 3.12 (the generator uses the standard library only).

```powershell
# Windows PowerShell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
python3.12 -m venv .venv
source .venv/bin/activate
```

### Generate data

```bash
# Full dataset: 1,000 documents, 5% errors -> data/ (git-ignored)
python src/generator/generate_data.py

# Options
python src/generator/generate_data.py --help
```

| Option | Default | Meaning |
|---|---|---|
| `--documents` | `1000` | Number of documents |
| `--error-rate` | `0.05` | Share of documents with one injected error |
| `--seed` | `42` | Random seed; the same seed gives identical files |
| `--fiscal-year` | `2025` | Fiscal year of the postings |
| `--output-dir` | `data` | Output directory |

### Reproduce the committed sample

`sample_data/` is a small sample that contains all six error types at least once:

```bash
python src/generator/generate_data.py --documents 20 --error-rate 0.3 --seed 1 --output-dir sample_data
```

Expected result: 8 cost centers, 18 headers, 83 line items, and
1 `missing_key`, 2 `line_without_header`, 2 `unbalanced_document`,
1 `zero_amount`, 2 `unknown_cost_center`, 1 `invalid_posting_date`.

## Repository layout

```
.
├── src/generator/generate_data.py   # synthetic COBK/COEP generator
├── sample_data/                     # small committed sample (csks, cobk, coep)
├── data/                            # full generated data (git-ignored)
├── CLAUDE.md                        # instructions for AI coding assistants
├── README.md                        # this file
└── LICENSE                          # MIT license
```

## Security

- Synthetic data only; no real company data.
- No secrets in the repository: `.env` files, keys and credentials are git-ignored.
- Google Cloud access will use Application Default Credentials. No service account key files.
- Docker ports will bind to `127.0.0.1` only.
- BigQuery: batch load jobs only (no streaming inserts) and partitioned tables.

## Tech stack

Python 3.12 · PostgreSQL 16 · Google BigQuery · dbt · Apache Airflow · Docker · GitHub Actions

## Author

Arsalan Al-aghbari, Data & AI Engineer · [LinkedIn](https://www.linkedin.com/in/arsalan-al-aghbari)

## License

MIT. See [LICENSE](LICENSE).
