# Databricks App

This folder contains the Streamlit app scaffold for the Data Readiness Desk.

The app must read cached gold outputs only. It should not train models, call AI functions, write Delta tables, or recompute scores during the live demo.

## Expected Gold Tables

- `drd.gold.facility_verdicts`
- `drd.gold.district_verdicts`
- `drd.gold.fix_ranking`
- `drd.gold.coverage_predictions`

## Local Shape

- [app.py](app.py): Streamlit app shell
- [app.yaml](app.yaml): Databricks Apps command and environment template
- [requirements.txt](requirements.txt): App runtime dependencies
