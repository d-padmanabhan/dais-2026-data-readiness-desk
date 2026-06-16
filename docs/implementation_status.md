# Implementation Status

This document maps Vibhu's [Requirements](requirements.md) and [Runbook](runbook.md) to the current repository state.

## Table of Contents

- [Implemented](#implemented)
- [Scaffolded](#scaffolded)
- [Remaining Build Work](#remaining-build-work)
- [Protect-First Demo Path](#protect-first-demo-path)

## Implemented

- Databricks bundle scaffold with dev, staging, and prod validation targets.
- Serverless-compatible Databricks job tasks and preflight source-file validation.
- PIN and NFHS foundation pipeline for bronze, silver, and gold readiness tables.
- PIN ambiguity handling with one-row-per-PIN readiness summaries.
- NFHS suppressed and low-sample parsing rules.
- Data contracts for PIN, NFHS, facilities, HMIS, SRS, and district boundaries.
- Databricks governance guidance for catalogs, grants, tags, storage, audit, and workspace binding.
- Pure Python readiness and Trust Verdict scoring helpers with tests.
- HMIS header/value parsing helpers for the currently uploaded state-grain file.
- HMIS curated annual indicator totals for ANC, institutional delivery, births, and immunization.
- HMIS state-grain fallback summary table for demo disease-lens exploration.
- Facilities shared table ingest with `silver_facilities_geo` output for 10,088 facility rows.
- First-pass `gold_facility_verdicts` output with 255 state/source-state rollups.
- Free Databricks App API reads cached `gold_hmis_state_indicator_summary` and `gold_facility_verdicts`.
- Free Databricks App deployed in dev as `data-readiness-desk`.
- Mermaid diagrams and decision log.
- GitHub Actions CI hardened for pre-commit and guarded Databricks validation.

## Scaffolded

- [data](../data/) source file folder and ingest guidance.
- [app](../app/) Free Databricks App shell that uses Vite, React, and Node.js inside Databricks Apps and reads the current cached gold outputs only.
- [config/scoring.yaml](../config/scoring.yaml) with score thresholds and quota-safety defaults.

## Remaining Build Work

- Decide whether the current state-grain HMIS file is sufficient as a fallback or whether the disease lens needs a district-grain HMIS extract from another source.
- Add point-in-polygon facility district assignment.
- Normalize HMIS denominators and publish comparable district rates.
- Build `gold_district_verdicts` and `gold_fix_ranking`.
- Add `ai_extract` for facility capability fields.
- Train AutoML once or publish a static fallback `gold_coverage_predictions` table.
- Wire the Free Databricks App to real cached gold tables.
- Add before/after fix rows for the live demo.

## Protect-First Demo Path

If time is short, prioritize:

1. Facility location/completeness trust using `gold_facility_verdicts`.
1. State-grain HMIS fallback using `gold_hmis_state_indicator_summary`.
1. One before/after fix flow from cached rows.
1. A clear explanation that model predictions and `ai_extract` are scaffolded or precomputed.
