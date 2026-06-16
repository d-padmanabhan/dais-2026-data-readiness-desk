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
- [Phase 6 - Free Databricks App](#phase-6---free-databricks-app)
- [Phase 7 - Deploy And Dry Run](#phase-7---deploy-and-dry-run)
- [CI Configuration](#ci-configuration)
- [Validation Checks](#validation-checks)
- [Export Workspace Reference Artifacts](#export-workspace-reference-artifacts)
- [Common Issues](#common-issues)
- [Quota-Safety Checklist](#quota-safety-checklist)

## Prerequisites

- Databricks CLI installed and authenticated.
- Unity Catalog enabled workspace.
- Permission to create or write tables in the chosen catalog and schema.
- Source CSV files uploaded to a Unity Catalog Volume.

## Source Files

Source files are tracked or staged under [data](../data/) before they are copied into a Unity Catalog Volume. Expected filenames:

- `india_post_pincode_directory.csv`
- `hmis_2019_20_slice.csv`
- `srs_2020_state.csv`
- `india_districts.geojson`

Copy file-based sources to `/Volumes/data_readiness_desk/bronze/files/` or the configured source volume before running the bronze notebook. Facilities and NFHS-5 are referenced as Databricks shared tables.

Current HMIS caveat: `hmis_2019_20_slice.csv` is present locally, but the inspected file is state-grain (`State`, `S.No.`, `Parameters`, `Type`, monthly value columns) and uses `cp1252` encoding. District-level disease reconciliation still needs either a district-grain HMIS extract or an explicit state-grain fallback story.

Build or fetch reproducible local source files:

```bash
just generate-srs
just fetch-boundaries
DATA_GOV_API_KEY="<your-data-gov-api-key>" just fetch-pincode
```

## Governance Notes

Review [Databricks Governance](governance.md), especially the [Databricks object hierarchy](governance.md#databricks-object-hierarchy), before creating non-dev catalogs, grants, or app identities. The hackathon defaults are intentionally lightweight, but production-style ownership should use groups or service principals, Unity Catalog Volumes or external locations, governed tags, and read-only app access to cached gold outputs.

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

Use the bootstrap script to create the catalog, table schema, upload Volume, and upload any available local files:

```bash
./scripts/bootstrap_databricks_workspace.sh --warehouse-id <warehouse-id>
```

If `DATABRICKS_WAREHOUSE_ID` is already set in your shell, the script can read it from the environment:

```bash
set -a
source "/Users/dpadmanabhan/code/labs/tmp/.env"
set +a

./scripts/bootstrap_databricks_workspace.sh \
  --catalog data_readiness_desk \
  --schema pipeline \
  --volume-schema bronze \
  --volume files
```

For the current workspace, the explicit warehouse form is:

```bash
./scripts/bootstrap_databricks_workspace.sh \
  --warehouse-id 4e307d33a4466b55 \
  --catalog data_readiness_desk \
  --schema pipeline \
  --volume-schema bronze \
  --volume files
```

The script runs the following SQL:

```sql
CREATE CATALOG IF NOT EXISTS data_readiness_desk;
CREATE SCHEMA IF NOT EXISTS data_readiness_desk.pipeline;
CREATE SCHEMA IF NOT EXISTS data_readiness_desk.bronze;
CREATE VOLUME IF NOT EXISTS data_readiness_desk.bronze.files;
```

It then uploads local files from [data](../data/) to the Volume:

```bash
databricks fs cp data/india_post_pincode_directory.csv dbfs:/Volumes/data_readiness_desk/bronze/files/
databricks fs cp data/hmis_2019_20_slice.csv dbfs:/Volumes/data_readiness_desk/bronze/files/
databricks fs cp data/srs_2020_state.csv dbfs:/Volumes/data_readiness_desk/bronze/files/
databricks fs cp data/india_districts.geojson dbfs:/Volumes/data_readiness_desk/bronze/files/
```

NFHS-5 may already exist as a provided Databricks table. Record its full table name before joining.

## Phase 1A - Grant Read Access

Grant least-privilege read access to a teammate or your own user after the catalog exists:

```bash
./scripts/grant_catalog_read_access.sh \
  --principal john.doe@acme.com \
  --warehouse-id 4e307d33a4466b55 \
  --catalog data_readiness_desk \
  --schema pipeline \
  --volume-schema bronze \
  --volume files
```

The script grants:

```sql
GRANT USE CATALOG ON CATALOG data_readiness_desk TO `<principal>`;
GRANT USE SCHEMA ON SCHEMA data_readiness_desk.pipeline TO `<principal>`;
GRANT SELECT ON SCHEMA data_readiness_desk.pipeline TO `<principal>`;
GRANT USE SCHEMA ON SCHEMA data_readiness_desk.bronze TO `<principal>`;
GRANT READ VOLUME ON VOLUME data_readiness_desk.bronze.files TO `<principal>`;
```

Grant the same read access to the Free Databricks App service principal before relying on the app API:

```bash
./scripts/grant_catalog_read_access.sh \
  --app-name data-readiness-desk \
  --warehouse-id 4e307d33a4466b55 \
  --catalog data_readiness_desk \
  --schema pipeline \
  --volume-schema bronze \
  --volume files
```

The script resolves `data-readiness-desk` to its Databricks-managed service principal before issuing grants. The current app principal is:

```text
service_principal_client_id: faacde25-a372-42b3-8e55-f3f24bd2dc32
service_principal_name: app-1zobg3 data-readiness-desk
```

Manual SQL fallback:

```sql
GRANT USE CATALOG ON CATALOG data_readiness_desk
  TO `faacde25-a372-42b3-8e55-f3f24bd2dc32`;

GRANT USE SCHEMA ON SCHEMA data_readiness_desk.pipeline
  TO `faacde25-a372-42b3-8e55-f3f24bd2dc32`;

GRANT SELECT ON SCHEMA data_readiness_desk.pipeline
  TO `faacde25-a372-42b3-8e55-f3f24bd2dc32`;
```

Why this matters: the app runs as its own Databricks-managed service principal, not as the interactive user who created the catalog. If that app principal lacks `USE CATALOG`, `USE SCHEMA`, and `SELECT`, the Node API can fail while the same SQL works from a local CLI session. A browser message such as `Unexpected token '<'` usually means the frontend tried to parse an HTML error page as JSON, often because the backend request hit an auth, app-startup, or permission failure.

## Phase 2 - Bronze Ingest

Goal: land every source as raw Delta once. Do not reread raw files in later phases.

Expected bronze tables:

- `data_readiness_desk.pipeline.bronze_facilities` sourced from the shared facilities table
- `data_readiness_desk.pipeline.bronze_india_post_pincode_directory`
- `data_readiness_desk.pipeline.bronze_hmis_2019_20_slice`
- `data_readiness_desk.pipeline.bronze_srs`
- `data_readiness_desk.pipeline.bronze_district_boundaries`

The current bundle already has bronze ingestion for PIN and NFHS foundation data. Extend it for facilities, HMIS, SRS, and district boundaries as files become available.

## Phase 3 - Silver Clean Normalize Resolve Geography

Silver is where grain discipline and denominator discipline live.

Build or extend these outputs:

- `data_readiness_desk.pipeline.silver_facilities_geo`: facility points with validated coordinates and source geography fields.
- `data_readiness_desk.pipeline.silver_pincode_lookup`: one row per PIN with ambiguity flags.
- `data_readiness_desk.pipeline.silver_nfhs_indicator_quality_long`: NFHS values with suppressed/low-sample flags.
- `data_readiness_desk.pipeline.silver_hmis_2019_20_long`: HMIS wide monthly values normalized to long form with `geo_grain`.
- `data_readiness_desk.pipeline.silver_srs_state`: state-grain weak anchor table.

Important rules:

- Use polygon-derived district as the primary facility district when valid coordinates exist.
- Keep `geo_grain` on every silver table: `point`, `district`, or `state`.
- Do not compare HMIS numerators to NFHS percentages until denominator logic is documented.
- The currently uploaded HMIS file is state-grain. District-level disease reconciliation needs a district-grain HMIS file or an explicit state-grain fallback story.

## Phase 4 - AutoML Classifier

Train or stub the model once, then batch-score to a gold table. Never train live during the demo.

Target output:

- `data_readiness_desk.pipeline.gold_coverage_predictions`

Recommended path:

1. Build `data_readiness_desk.pipeline.silver_disease_training` from districts where NFHS and HMIS agree enough for training.
1. Train AutoML once with a small timeout.
1. Register the model or document a static fallback.
1. Batch-score all demo entities and write predictions to gold.

If time is short, publish a static `coverage_predictions` table and say clearly in the pitch that it is the fallback path.

## Phase 5 - Gold Score Everything

Gold is the app contract. Compute all verdicts and fixes before the demo.

Expected gold outputs:

- `data_readiness_desk.pipeline.gold_facility_verdicts`
- `data_readiness_desk.pipeline.gold_district_verdicts`
- `data_readiness_desk.pipeline.gold_fix_ranking`
- `data_readiness_desk.pipeline.gold_coverage_predictions`
- `data_readiness_desk.pipeline.gold_facility_caps`

Rules:

- Numeric score is a weighted average.
- Band is weakest-link capped.
- Suppressed, blank, or low-confidence values can never produce a green verdict.
- `ai_extract` values from facility `capability` text get partial provenance confidence.
- Before/after demo rows must be precomputed so the app only swaps cached rows.

## Phase 6 - Free Databricks App

The app lives under [app](../app/) and must run as a Free Databricks App. The current scaffold uses Vite, React, and Node.js inside Databricks Apps; do not deploy this as an external web service. The app must read cached gold tables only.

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
./scripts/deploy_databricks_app.sh
```

The script creates the `data-readiness-desk` app if needed, syncs [app](../app/) to the current Databricks user's workspace, starts app compute, and deploys a snapshot.

Current dev app URL:

[Data Readiness Desk App](https://data-readiness-desk-7474647240221945.aws.databricksapps.com)

Grant viewer access to a workspace user or group:

```bash
./scripts/grant_databricks_app_access.sh --user john.doe@acme.com
./scripts/grant_databricks_app_access.sh --group users
```

The app URL is not anonymous internet-public. External viewers still need Databricks workspace access and `CAN_USE` on the app. For hackathon sharing, grant `CAN_USE` to the smallest appropriate workspace group or named users.

Dry-run acceptance criteria:

- Location lens reads cached facility trust rollups derived from 10,088 shared-table facility rows.
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

Query cached readiness outputs:

```bash
./scripts/query_readiness_outputs.sh --warehouse-id <warehouse-id>
```

## Export Workspace Reference Artifacts

Some design artifacts can be created in the Databricks workspace during the hackathon. Export them into the repo only as reference material unless they have been reviewed and promoted into the canonical bundle notebooks or app code.

Use these commands to export the current Genie-generated artifacts:

```bash
databricks workspace export \
  "/Workspace/Users/john.doe@acme.com/Data Readiness Desk - Pipeline Transforms" \
  --format SOURCE \
  --file "notebooks/genie_pipeline_transforms.py"

databricks workspace export \
  "/Workspace/Users/john.doe@acme.com/Data Readiness Desk - App Integration" \
  --format SOURCE \
  --file "notebooks/genie_app_integration.py"

databricks workspace export \
  "/Workspace/Users/john.doe@acme.com/HACKATHON_SETUP_README.md" \
  --format SOURCE \
  --file "docs/genie/hackathon_setup.md"
```

> [!NOTE]
> Treat exported workspace artifacts as reference snapshots. The canonical implementation lives in [databricks.yml](../databricks.yml), [notebooks](../notebooks/), [app](../app/), and [src/data_readiness_desk](../src/data_readiness_desk/).

Use `data-readiness-desk@acme.com` as the placeholder contact address in documentation examples. Do not use a personal address unless we explicitly decide to publish one.

Manual notebook order:

1. [00_preflight.py](../notebooks/00_preflight.py)
1. [01_ingest_bronze.py](../notebooks/01_ingest_bronze.py)
1. [02_build_silver.py](../notebooks/02_build_silver.py)
1. [03_build_gold.py](../notebooks/03_build_gold.py)
1. [04_demo_queries.py](../notebooks/04_demo_queries.py)

- Preflight should fail fast if the source Volume path or required files are missing.
- `pipeline_run_summary` should show a row count for bronze source tables.
- `silver_pincode_lookup` should have one row per PIN code.
- `silver_nfhs_indicator_quality_long` should have one row per district and indicator cell.
- `silver_hmis_2019_20_long` should show state-grain long-form rows with `geo_grain=state`.
- `silver_hmis_2019_20_indicator_totals` should include annual totals for ANC, institutional delivery, births, and immunization demo measures.
- `gold_hmis_state_indicator_summary` should publish state-grain fallback ratios with a caveat.
- `pipeline_quality_checks` should show `pass` for required column and indicator-detection checks.
- `gold_pincode_health_enrichment` should show match statuses, not just matched rows.
- `gold_underserved_district_candidates` should produce ranked districts.
- App tables such as `gold_facility_verdicts`, `gold_district_verdicts`, and `gold_fix_ranking` should be precomputed before the Free Databricks App demo.

## Common Issues

### Cannot Create Catalog

The ingestion notebook calls `CREATE CATALOG IF NOT EXISTS`. If your hackathon workspace does not allow catalog creation, create the catalog manually or ask an admin. You can also remove that line and keep `CREATE SCHEMA IF NOT EXISTS` if the catalog already exists.

### Source Files Not Found

Confirm the file paths in the Volume:

```bash
databricks fs ls dbfs:/Volumes/data_readiness_desk/bronze/files/
```

The default file names are:

- `india_post_pincode_directory.csv`
- `nfhs5_district_health_indicators.csv`

### NFHS Geography Columns Not Detected

The silver notebook looks for common normalized names such as `state`, `state_ut`, `district`, and `district_name`. If your extract uses different geography headings, update the `first_existing` candidate lists in [notebooks/02_build_silver.py](../notebooks/02_build_silver.py).

### Metrics Are Null in the Underserved Candidate Table

The gold notebook discovers likely columns by substring. If your NFHS extract uses different indicator wording, update the `find_metric` terms in [notebooks/03_build_gold.py](../notebooks/03_build_gold.py).

### App API Returns HTML Instead Of JSON

Symptom: the browser or React app reports that `/api/readiness-summary` received HTML instead of JSON.

Likely causes:

- The app backend is not running, so Databricks Apps returns an HTML error page.
- `DATABRICKS_HOST` is malformed. The server normalizes bare hostnames to `https://...`, but non-HTTPS values are rejected.
- The app service principal cannot read Unity Catalog objects.

Diagnosis:

```bash
databricks apps get data-readiness-desk --output json
databricks apps logs data-readiness-desk --tail-lines 100
```

Permission fix:

```bash
./scripts/grant_catalog_read_access.sh \
  --app-name data-readiness-desk \
  --warehouse-id 4e307d33a4466b55
```

Then redeploy:

```bash
./scripts/deploy_databricks_app.sh
```

## Quota-Safety Checklist

- [ ] All verdicts are precomputed to gold; app issues `SELECT` statements only.
- [ ] Model trained once, predictions batch-scored to a table.
- [ ] Genie calls are user-initiated and cached, or replaced with a keyword parser for demo.
- [ ] No `.write`, model training, or raw ingest cells run during the live demo.
- [ ] Data slices stay small.
- [ ] One serverless SQL Warehouse is started before demo and reused for app queries.
