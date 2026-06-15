# Runbook

This runbook covers the first Databricks execution path.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Validate Configuration](#validate-configuration)
- [Deploy and Run](#deploy-and-run)
- [Manual Notebook Run Order](#manual-notebook-run-order)
- [Validation Checks](#validation-checks)
- [Common Issues](#common-issues)

## Prerequisites

- Databricks CLI installed and authenticated.
- Unity Catalog enabled workspace.
- Permission to create or write tables in the chosen catalog and schema.
- Source CSV files uploaded to a Unity Catalog Volume.

## Validate Configuration

From the project root:

```bash
databricks bundle validate --target dev
```

If validation fails because the CLI cannot find a profile, authenticate first:

```bash
databricks auth login
```

## Deploy and Run

```bash
databricks bundle deploy --target dev
databricks bundle run virtue_foundation_pipeline --target dev
```

Use variable overrides when your catalog, schema, or source volume path differs from the defaults:

```bash
databricks bundle run virtue_foundation_pipeline --target dev --var catalog=my_catalog --var schema=my_schema --var source_volume_path=/Volumes/my_catalog/my_schema/raw
```

## Manual Notebook Run Order

1. [01_ingest_bronze.py](../notebooks/01_ingest_bronze.py)
1. [02_build_silver.py](../notebooks/02_build_silver.py)
1. [03_build_gold.py](../notebooks/03_build_gold.py)
1. [04_demo_queries.py](../notebooks/04_demo_queries.py)

## Validation Checks

After a successful run:

- `pipeline_run_summary` should show a row count for both bronze source tables.
- `silver_pincode_lookup` should have one row per PIN code.
- `silver_nfhs_indicator_quality_long` should have one row per district and indicator cell.
- `pipeline_quality_checks` should show `pass` for required column and indicator-detection checks.
- `gold_pincode_health_enrichment` should show match statuses, not just matched rows.
- `gold_underserved_district_candidates` should produce ranked districts.

## Common Issues

### Cannot Create Catalog

The ingestion notebook calls `CREATE CATALOG IF NOT EXISTS`. If your hackathon workspace does not allow catalog creation, create the catalog manually or ask an admin. You can also remove that line and keep `CREATE SCHEMA IF NOT EXISTS` if the catalog already exists.

### Source Files Not Found

Confirm the file paths in the Volume:

```bash
databricks fs ls dbfs:/Volumes/<catalog>/<schema>/raw
```

The default file names are:

- `india_post_pincode_directory.csv`
- `nfhs5_district_health_indicators.csv`

### NFHS Geography Columns Not Detected

The silver notebook looks for common normalized names such as `state`, `state_ut`, `district`, and `district_name`. If your extract uses different geography headings, update the `first_existing` candidate lists in [notebooks/02_build_silver.py](../notebooks/02_build_silver.py).

### Metrics Are Null in the Underserved Candidate Table

The gold notebook discovers likely columns by substring. If your NFHS extract uses different indicator wording, update the `find_metric` terms in [notebooks/03_build_gold.py](../notebooks/03_build_gold.py).
