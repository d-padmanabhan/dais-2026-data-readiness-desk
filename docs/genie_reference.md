# Genie Reference Exports

Genie/workspace artifacts were exported with the Databricks CLI on 2026-06-16 and kept as local reference snapshots under `tmp/genie_exports/`.

These exports are not canonical source. Several exported files still mention the old bundle name, old workspace paths, and earlier Streamlit/App guidance. The canonical implementation remains:

- [databricks.yml](../databricks.yml)
- [notebooks](../notebooks/)
- [app](../app/)
- [scripts](../scripts/)
- [src/data_readiness_desk](../src/data_readiness_desk/)

## Useful Learnings Promoted

- The Free Databricks App needed an explicit deploy step after the bundle pipeline was deployed.
- The app should deploy from the current [app](../app/) directory, not from exported bundle snapshots.
- The app should read cached gold outputs only:
  - `data_readiness_desk.pipeline.gold_hmis_state_indicator_summary`
  - `data_readiness_desk.pipeline.gold_facility_verdicts`
- Raw exported notebooks can be useful for future ideas, but they must be reviewed and adapted before use because they include stale schema names and non-canonical app patterns.

## Current App Deployment

- App name: `data-readiness-desk`
- Dev URL: [Data Readiness Desk App](https://data-readiness-desk-7474647240221945.aws.databricksapps.com)
- Active deployment: `01f1693fbd021e7cbf40f6b974aeeade`
