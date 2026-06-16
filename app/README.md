# Databricks App

This folder contains the Free Databricks App scaffold for the Data Readiness Desk. It uses a Vite React client served by a small Node.js server.

The app must read cached gold outputs only. It should not train models, call AI functions, write Delta tables, or recompute scores during the live demo.

## Expected Gold Tables

- `data_readiness_desk.pipeline.gold_facility_verdicts`
- `data_readiness_desk.pipeline.gold_district_verdicts`
- `data_readiness_desk.pipeline.gold_fix_ranking`
- `data_readiness_desk.pipeline.gold_coverage_predictions`

## Local Shape

- [client](client): Vite React client
- [server/index.mjs](server/index.mjs): Node.js static server and API placeholder
- [app.yaml](app.yaml): Databricks Apps command and environment template
- [package.json](package.json): Node.js app dependencies and scripts
