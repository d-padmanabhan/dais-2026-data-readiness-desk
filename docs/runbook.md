# Data Readiness Desk Runbook

This runbook is the single source of truth for setting up, building, validating, and demoing the Data Readiness Desk.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Source Files](#source-files)
- [Governance Notes](#governance-notes)
- [Phase 0 - Local Setup](#phase-0---local-setup)
- [Phase 1 - Provision Unity Catalog](#phase-1---provision-unity-catalog)
- [Phase 2 - Bronze Ingest](#phase-2---bronze-ingest)
- [Phase 3 - Silver Clean Normalize Resolve Geography](#phase-3---silver-clean-normalize-resolve-geography)
- [Phase 4 - AutoML Classifier](#phase-4---automl-classifier)
- [Phase 5 - Gold Score Everything](#phase-5---gold-score-everything)
- [Phase 6 - Streamlit App](#phase-6---streamlit-app)
- [Phase 7 - Deploy And Dry Run](#phase-7---deploy-and-dry-run)
- [CI Configuration](#ci-configuration)
- [Validation Checks](#validation-checks)
- [Common Issues](#common-issues)
- [Quota-Safety Checklist](#quota-safety-checklist)

## Prerequisites

- Databricks CLI installed and authenticated.
- Unity Catalog enabled workspace.
- Permission to create or write tables in the chosen catalog and schema.
- Source CSV files uploaded to a Unity Catalog Volume.

## Source Files

Source files are tracked or staged under [data](../data/) before they are copied into a Unity Catalog Volume. Expected filenames:

- `facilities.xlsx`
- `india_post_pincode_directory.csv`
- `hmis_2019_20_slice.csv`
- `srs_2020_state.csv`
- `india_districts.geojson`

Copy these files to `/Volumes/drd/bronze/files/` or the configured source volume before running the bronze notebook. NFHS-5 may be referenced as a provided Databricks table instead of a local file.

Current HMIS caveat: `hmis_2019_20_slice.csv` is present locally, but the inspected file is state-grain (`State`, `S.No.`, `Parameters`, `Type`, monthly value columns) and uses `cp1252` encoding. District-level disease reconciliation still needs either a district-grain HMIS extract or an explicit state-grain fallback story.

## Governance Notes

Review [Databricks Governance](governance.md) before creating non-dev catalogs, grants, or app identities. The hackathon defaults are intentionally lightweight, but production-style ownership should use groups or service principals, Unity Catalog Volumes or external locations, governed tags, and read-only app access to cached gold outputs.

## Phase 0 - Local Setup

```bash
# Databricks CLI v0.250.0+ required for apps + bundles
databricks -v

# Service-principal OAuth. Do not commit real values.
export DATABRICKS_HOST="https://<workspace-host>"
export DATABRICKS_CLIENT_ID="<service-principal-client-id>"
export DATABRICKS_CLIENT_SECRET="<service-principal-secret>"

# Verify workspace access.
databricks current-user me
```

Install local tooling and run the first validation pass:

```bash
just install
just ci
databricks bundle validate --target dev
```

## Phase 1 - Provision Unity Catalog

Create the demo catalog, schemas, and upload Volume:

```sql
CREATE CATALOG IF NOT EXISTS drd;
CREATE SCHEMA IF NOT EXISTS drd.bronze;
CREATE SCHEMA IF NOT EXISTS drd.silver;
CREATE SCHEMA IF NOT EXISTS drd.gold;
CREATE VOLUME IF NOT EXISTS drd.bronze.files;
```

Upload local files from [data](../data/) to the Volume:

```bash
databricks fs cp data/Facilities.xlsx dbfs:/Volumes/drd/bronze/files/
databricks fs cp data/india_post_pincode_directory.csv dbfs:/Volumes/drd/bronze/files/
databricks fs cp data/hmis_2019_20_slice.csv dbfs:/Volumes/drd/bronze/files/
databricks fs cp data/srs_2020_state.csv dbfs:/Volumes/drd/bronze/files/
databricks fs cp data/india_districts.geojson dbfs:/Volumes/drd/bronze/files/
```

NFHS-5 may already exist as a provided Databricks table. Record its full table name before joining.

## Phase 2 - Bronze Ingest

Goal: land every source as raw Delta once. Do not reread raw files in later phases.

Expected bronze tables:

- `drd.bronze.facilities`
- `drd.bronze.pincode`
- `drd.bronze.hmis`
- `drd.bronze.srs`
- `drd.bronze.district_boundaries`

The current bundle already has bronze ingestion for PIN and NFHS foundation data. Extend it for facilities, HMIS, SRS, and district boundaries as files become available.

## Phase 3 - Silver Clean Normalize Resolve Geography

Silver is where grain discipline and denominator discipline live.

Build or extend these outputs:

- `drd.silver.facilities_geo`: facility points assigned to district polygons where valid coordinates exist.
- `drd.silver.pincode_lookup`: one row per PIN with ambiguity flags.
- `drd.silver.nfhs_indicator_quality_long`: NFHS values with suppressed/low-sample flags.
- `drd.silver.hmis_long`: HMIS wide monthly values normalized to long form with `geo_grain`.
- `drd.silver.srs_state`: state-grain weak anchor table.

Important rules:

- Use polygon-derived district as the primary facility district when valid coordinates exist.
- Keep `geo_grain` on every silver table: `point`, `district`, or `state`.
- Do not compare HMIS numerators to NFHS percentages until denominator logic is documented.
- The currently uploaded HMIS file is state-grain. District-level disease reconciliation needs a district-grain HMIS file or an explicit state-grain fallback story.

## Phase 4 - AutoML Classifier

Train or stub the model once, then batch-score to a gold table. Never train live during the demo.

Target output:

- `drd.gold.coverage_predictions`

Recommended path:

1. Build `drd.silver.disease_training` from districts where NFHS and HMIS agree enough for training.
1. Train AutoML once with a small timeout.
1. Register the model or document a static fallback.
1. Batch-score all demo entities and write predictions to gold.

If time is short, publish a static `coverage_predictions` table and say clearly in the pitch that it is the fallback path.

## Phase 5 - Gold Score Everything

Gold is the app contract. Compute all verdicts and fixes before the demo.

Expected gold outputs:

- `drd.gold.facility_verdicts`
- `drd.gold.district_verdicts`
- `drd.gold.fix_ranking`
- `drd.gold.coverage_predictions`
- `drd.gold.facility_caps`

Rules:

- Numeric score is a weighted average.
- Band is weakest-link capped.
- Suppressed, blank, or low-confidence values can never produce a green verdict.
- `ai_extract` values from facility `capability` text get partial provenance confidence.
- Before/after demo rows must be precomputed so the app only swaps cached rows.

## Phase 6 - Streamlit App

The app lives under [app](../app/) and must read cached gold tables only.

UI requirements:

- Search box plus lens toggle: Location, Disease / Condition, Facility.
- Verdict card: band, numeric score, one-line binding reason.
- Map or table colored by verdict.
- Ranked fix panel with estimated score lift and impact weight.
- Before/after interaction from cached rows.

Genie, if used, must be user-initiated and cached. Do not call Genie on keystroke or page load.

## Phase 7 - Deploy And Dry Run

Create and deploy the Databricks App after gold tables exist:

```bash
databricks apps create drd-desk
databricks sync ./app /Workspace/Users/<principal-or-user>/drd-app
databricks apps deploy drd-desk --source-code-path /Workspace/Users/<principal-or-user>/drd-app
```

Dry-run acceptance criteria:

- Location lens scores all 100 facilities from cached data.
- Disease lens reconciles NFHS/HMIS institutional delivery for at least one demo district or documented state-grain fallback.
- Model predictions table exists.
- `ai_extract` output exists for at least one facility and is tagged partial-confidence.
- Verdict card shows band, number, and reason.
- Ranked fixes render.
- One before/after re-score works from cached rows.
- No live recompute or live training runs during the demo.

## CI Configuration

The GitHub Actions workflow validates the Databricks bundle when OAuth service-principal secrets are configured in GitHub:

- `DATABRICKS_HOST`
- `DATABRICKS_CLIENT_ID`
- `DATABRICKS_CLIENT_SECRET`

Set repository variable `ENABLE_DATABRICKS_STAGING_DEPLOY=1` only after the staging workspace and catalog are ready. When enabled, pushes to `main` deploy the Declarative Automation Bundle to the `staging` target.

## Validation Checks

From the project root:

```bash
databricks bundle validate --target dev
```

If validation fails because credentials are missing, use service-principal OAuth:

```bash
export DATABRICKS_HOST="https://<workspace-host>"
export DATABRICKS_CLIENT_ID="<service-principal-client-id>"
export DATABRICKS_CLIENT_SECRET="<service-principal-secret>"
databricks current-user me
```

Then validate and run:

```bash
databricks bundle validate --target dev
databricks bundle deploy --target dev
databricks bundle run virtue_foundation_pipeline --target dev
```

Manual notebook order:

1. [01_ingest_bronze.py](../notebooks/01_ingest_bronze.py)
1. [02_build_silver.py](../notebooks/02_build_silver.py)
1. [03_build_gold.py](../notebooks/03_build_gold.py)
1. [04_demo_queries.py](../notebooks/04_demo_queries.py)

- `pipeline_run_summary` should show a row count for both bronze source tables.
- `silver_pincode_lookup` should have one row per PIN code.
- `silver_nfhs_indicator_quality_long` should have one row per district and indicator cell.
- `silver_hmis_2019_20_long` should show state-grain long-form rows with `geo_grain=state`.
- `pipeline_quality_checks` should show `pass` for required column and indicator-detection checks.
- `gold_pincode_health_enrichment` should show match statuses, not just matched rows.
- `gold_underserved_district_candidates` should produce ranked districts.
- App tables such as `gold_facility_verdicts`, `gold_district_verdicts`, and `gold_fix_ranking` should be precomputed before the Streamlit app demo.

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

## Quota-Safety Checklist

- [ ] All verdicts are precomputed to gold; app issues `SELECT` statements only.
- [ ] Model trained once, predictions batch-scored to a table.
- [ ] Genie calls are user-initiated and cached, or replaced with a keyword parser for demo.
- [ ] No `.write`, model training, or raw ingest cells run during the live demo.
- [ ] Data slices stay small.
- [ ] One serverless SQL Warehouse is started before demo and reused for app queries.
