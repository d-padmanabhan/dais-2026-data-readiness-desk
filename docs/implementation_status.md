# Implementation Status

This document maps Vibhu's [Requirements](requirements.md) and [Runbook](runbook.md) to the current repository state.

## Table of Contents

- [Implemented](#implemented)
- [Scaffolded](#scaffolded)
- [Remaining Build Work](#remaining-build-work)
- [Protect-First Demo Path](#protect-first-demo-path)

## Implemented

- Databricks bundle scaffold with dev, staging, and prod validation targets.
- PIN and NFHS foundation pipeline for bronze, silver, and gold readiness tables.
- PIN ambiguity handling with one-row-per-PIN readiness summaries.
- NFHS suppressed and low-sample parsing rules.
- Data contracts for PIN, NFHS, facilities, HMIS, SRS, and district boundaries.
- Databricks governance guidance for catalogs, grants, tags, storage, audit, and workspace binding.
- Pure Python readiness and Trust Verdict scoring helpers with tests.
- HMIS header/value parsing helpers for the currently uploaded state-grain file.
- Mermaid diagrams and decision log.
- GitHub Actions CI hardened for pre-commit and guarded Databricks validation.

## Scaffolded

- [data](../data/) landing folder for Vibhu's uploaded files.
- [app](../app/) Streamlit Databricks App shell that reads cached gold outputs only.
- [config/scoring.yaml](../config/scoring.yaml) with score thresholds and quota-safety defaults.

## Remaining Build Work

- Ingest `Facilities.xlsx`, SRS, and `india_districts.geojson`.
- Decide whether the current state-grain HMIS file is sufficient as a fallback or whether Vibhu will upload a district-grain HMIS extract.
- Add point-in-polygon facility district assignment.
- Normalize HMIS denominators and publish comparable district rates.
- Build `gold_facility_verdicts`, `gold_district_verdicts`, and `gold_fix_ranking`.
- Add `ai_extract` for facility capability fields.
- Train AutoML once or publish a static fallback `gold_coverage_predictions` table.
- Wire the Streamlit app to real cached gold tables.
- Add before/after fix rows for the live demo.

## Protect-First Demo Path

If time is short, prioritize:

1. Location lens for the 100 facilities.
1. Institutional-delivery NFHS/HMIS corroboration for at least one district.
1. One before/after fix flow from cached rows.
1. A clear explanation that model predictions and `ai_extract` are scaffolded or precomputed.
