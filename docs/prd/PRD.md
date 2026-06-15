# Data Readiness Desk PRD

This PRD summarizes the current product state, what is built, and what remains for the DAIS 2026 hackathon.

## Product Goal

A health planner asks, "Can I trust the data for this place, condition, or facility?" The Data Readiness Desk returns a Trust Verdict with a band, numeric score, binding reason, ranked fixes, and a before/after demonstration from cached outputs.

The product answers whether the data is actionable for planning, not whether a district is healthy.

## Current Build State

Implemented:

- Databricks bundle with dev, staging, and prod validation targets.
- Service-principal OAuth guidance and CI validation.
- PIN/NFHS foundation pipeline.
- HMIS bronze ingest using Windows-1252 decoding.
- HMIS silver long-form table.
- Curated HMIS annual indicator totals.
- Gold state-grain HMIS fallback summary.
- Data contracts for expected source files.
- Pure Python helpers for normalization, readiness, HMIS parsing, and Trust Verdict scoring.
- Free Databricks App scaffold that uses Vite, React, and Node.js inside Databricks Apps and is read-only by design.
- Governance, decision log, diagrams, data dictionary, and consolidated runbook.
- GitHub Actions, pre-commit, secret scanning, and local quality tooling.

Current source availability:

- Present locally: `data/hmis_2019_20_slice.csv`, `data/srs_2020_state.csv`, `data/india_districts.geojson`
- Available as Databricks shared table: facilities
- Not currently present locally: `india_post_pincode_directory.csv`
- NFHS-5 is expected as a Databricks shared table.

## Non-Goals

- Do not declare which conflicting public source is "true."
- Do not run model training or score recomputation during the live demo.
- Do not present PIN-derived geography as exact when ambiguous.
- Do not build a broad production platform; keep this hackathon-scoped but production-shaped.

## Constraints

- Databricks Free Edition quota: precompute all expensive results.
- The UI must run as a Free Databricks App; no external web hosting.
- App reads cached gold outputs only.
- Genie calls must be user-initiated and cached if used.
- Automation uses service-principal OAuth, not personal access tokens.
- Source files should be copied into Unity Catalog Volumes before Databricks jobs run.

## Key Architecture Decisions

- Use `data_readiness_desk` as the explicit namespace instead of `drd`.
- Keep the current bundle table model as one configured schema with layer-prefixed table names for now.
- Treat HMIS as state-grain fallback until a district-grain extract exists.
- Keep diagrams in Mermaid as the version-controlled source of truth.
- Use Unity Catalog governance concepts even in the hackathon build: owners, tags, grants, lineage, and system tables.

## Acceptance Criteria

- Location lens scores all facility records from cached data.
- Disease lens demonstrates at least one NFHS/HMIS trust verdict or documented state-grain fallback.
- Free Databricks App shows verdict card, reason, ranked fixes, and cached before/after behavior.
- `ai_extract` output exists or is explicitly scaffolded as the fallback.
- AutoML predictions exist or a static fallback table is documented.
- Live demo runs without raw ingest, writes, model training, or recomputation.

## Open Risks

- Facility and boundary files are not currently present locally.
- Current HMIS file is state-grain, not district-grain.
- App still uses placeholder UI until real gold verdict tables are available.
- Gold verdict and fix-ranking tables are not yet implemented.
- Bundle defaults are validated, but source Volume creation/upload still needs execution in Databricks.
