# Databricks App

This folder contains the Free Databricks App scaffold for the Data Readiness Desk. It uses a Vite React client served by a small Node.js server.

The app must read cached gold outputs only. It should not train models, call AI functions, write Delta tables, or recompute scores during the live demo.

## Current Gold Tables

- `data_readiness_desk.pipeline.gold_facility_verdicts`
- `data_readiness_desk.pipeline.gold_hmis_state_indicator_summary`

The Node.js server exposes `/api/readiness-summary`, which reads the current cached gold outputs through the Databricks SQL Statement API. The app is intentionally read-only for demo safety.

## Planned Gold Tables

- `data_readiness_desk.pipeline.gold_district_verdicts`
- `data_readiness_desk.pipeline.gold_fix_ranking`
- `data_readiness_desk.pipeline.gold_coverage_predictions`

## Local Shape

- [client](client): Vite React client
- [server/index.mjs](server/index.mjs): Node.js static server and API placeholder
- [app.yaml](app.yaml): Databricks Apps command and environment template
- [package.json](package.json): Node.js app dependencies and scripts

## Deployment

Deploy from the repository root:

```bash
./scripts/deploy_databricks_app.sh
```

Current dev app:

[Data Readiness Desk App](https://data-readiness-desk-7474647240221945.aws.databricksapps.com)

## App Permissions

There are two permission layers:

1. Viewer access to open the Databricks App.
2. Unity Catalog read access for the app's Databricks-managed service principal.

Grant viewer access to a workspace user or group:

```bash
./scripts/grant_databricks_app_access.sh --user john.doe@acme.com
./scripts/grant_databricks_app_access.sh --group users
```

Grant the app service principal read access before using the app API:

```bash
./scripts/grant_catalog_read_access.sh \
  --app-name data-readiness-desk \
  --warehouse-id 4e307d33a4466b55
```

The helper resolves the app's Databricks-managed service principal and grants `USE CATALOG`, `USE SCHEMA`, and `SELECT` on `data_readiness_desk.pipeline`.

If `/api/readiness-summary` returns HTML instead of JSON, check app logs and verify the app service principal has those grants. HTML usually means the browser received an app/auth error page instead of the JSON API payload.

The app URL is not anonymous internet-public. Viewers still need Databricks workspace access plus `CAN_USE` on the app.
