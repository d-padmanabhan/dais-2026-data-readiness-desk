# Databricks Governance

This project is a hackathon build, but the governance posture should still be explicit so future engineers know which shortcuts are demo-only and which patterns should carry forward.

## Table of Contents

- [Governance Model](#governance-model)
- [Databricks Object Hierarchy](#databricks-object-hierarchy)
- [Catalog And Schema Pattern](#catalog-and-schema-pattern)
- [Ownership And Grants](#ownership-and-grants)
- [Tags And Classification](#tags-and-classification)
- [Storage And Volumes](#storage-and-volumes)
- [Workspace Binding](#workspace-binding)
- [Audit And Lineage](#audit-and-lineage)
- [Hackathon Exceptions](#hackathon-exceptions)
- [Review Checklist](#review-checklist)

## Governance Model

Use Unity Catalog as the governance plane for tables, volumes, functions, models, lineage, and access controls.

Recommended default:

- Use account-level groups and service principals for Unity Catalog grants.
- Avoid workspace-local groups as governance primitives.
- Own production objects with groups or service principals, not individual users.
- Keep service-principal permissions scoped to the workload.

## Databricks Object Hierarchy

The main Databricks control and data objects are:

- Account: top-level billing and admin boundary. An account contains one or more workspaces and is managed by account admins.
- Workspace: isolated Databricks environment where users collaborate. A workspace contains notebooks, queries, dashboards, jobs, and related workspace assets.
- Metastore: Unity Catalog metadata and governance layer that can be shared across workspaces. A metastore contains catalogs and governs data access.
- Catalog: top-level container for schemas. In `databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities`, `databricks_virtue_foundation_dataset_dais_2026` is the catalog.
- Schema: container for tables, views, functions, and volumes. In the same example, `virtue_foundation_dataset` is the schema.
- Table, view, volume, or function: actual data object. In the same example, `facilities` is the table.
- Columns: fields inside a table, such as `name`, `latitude`, or `longitude`.
- Rows: actual data records.

Fully qualified table names follow this pattern:

```text
catalog.schema.table
```

Example:

```text
databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
```

Compute resources, such as the Serverless SQL Warehouse, sit alongside this data hierarchy. They execute queries against governed objects, but they are not part of the storage hierarchy.

## Catalog And Schema Pattern

The hackathon examples use a compact demo catalog such as `data_readiness_desk` or the configured bundle catalog. For a production version, choose a catalog model intentionally:

- Environment-first: `dev.raw`, `stage.curated`, `prod.serving`
- Domain-first: `healthcare.raw`, `healthcare.curated`, `healthcare.serving`
- Hybrid: `prod_healthcare.raw`, `prod_healthcare.curated`, `prod_healthcare.serving`

For this repo, the medallion layout should remain explicit:

- `bronze`: source-aligned, replayable data
- `silver`: normalized data with quality flags and geography resolution
- `gold`: cached Trust Verdicts, fix rankings, predictions, and app-ready outputs

## Ownership And Grants

Expected ownership and grant pattern:

- Pipeline service principal or data engineering group owns bronze/silver/gold write paths.
- App service principal gets read-only access to gold tables.
- Analysts get `SELECT` on gold or serving views, not raw data by default.
- Data stewards can apply governed tags where needed.
- Avoid broad `ALL PRIVILEGES` grants.

Suggested privilege shape:

| Principal | Bronze | Silver | Gold |
| --- | --- | --- | --- |
| Pipeline service principal | `MODIFY`, `SELECT` | `MODIFY`, `SELECT` | `MODIFY`, `SELECT` |
| App service principal | none | none | `SELECT` |
| Data analysts | none | optional `SELECT` | `SELECT` |
| Data stewards | `BROWSE`, `APPLY TAG` | `BROWSE`, `APPLY TAG` | `BROWSE`, `APPLY TAG` |

## Tags And Classification

Tag data objects before they become app-facing. At minimum, use:

- `owner`
- `environment`
- `cost_center`
- `data_sensitivity`
- `source`
- `geo_grain`
- `pipeline`

Recommended source classifications:

| Dataset | Sensitivity | Notes |
| --- | --- | --- |
| Facilities | event dataset | Treat as hackathon slice; review before public redistribution |
| PIN directory | public | Published under Government Open Data License - India |
| NFHS-5 | public | Preserve suppressed and low-sample flags |
| HMIS slice | public | Keep source period visible |
| SRS 2020 | public | State-grain weak anchor only |
| District boundaries | public | Document source and boundary vintage |

## Storage And Volumes

Use Unity Catalog Volumes or external locations for source files. Do not place cloud credentials in notebooks, job parameters, or repo files.

Expected hackathon flow:

1. Source files are staged under [data](../data/).
1. Files are copied into a Unity Catalog Volume such as `/Volumes/data_readiness_desk/bronze/files/`.
1. Bronze notebooks read each file once and write Delta tables.
1. Later phases read Delta tables only.

## Workspace Binding

Production catalogs should be bound only to production workspaces. The bundle currently uses the deploying principal workspace root for dev, staging, and prod targets to avoid broad `/Workspace/Shared` write exposure.

Before a production deployment, decide:

- Which workspace can access each catalog.
- Which groups can browse versus read.
- Which service principal owns deployment and writes.
- Whether the app should read direct gold tables or governed serving views.

## Audit And Lineage

Use system tables and Unity Catalog lineage to prove what the app is using.

Minimum audit questions:

- Who granted access to gold tables?
- Which job wrote each gold table version?
- Which source tables contributed to each Trust Verdict?
- Which queries are used by the app?
- Which jobs or queries are driving cost?

Useful system areas:

- `system.access.audit`
- table and column lineage system tables
- `system.billing.usage`
- `system.query.history`

## Hackathon Exceptions

These are acceptable for the hackathon but should be revisited before production:

- Small local `data/` landing folder before upload to a Unity Catalog Volume.
- Demo catalog naming such as `data_readiness_desk`.
- Free Databricks App scaffold with placeholder cached-read behavior.
- Static fallback predictions if AutoML cannot be completed in time.
- Limited source slices for HMIS and facilities.

These are not acceptable even for the demo:

- Committing secrets or raw private credentials.
- Calling Genie on every render or keystroke.
- Training or recomputing scores during the live demo.
- Presenting PIN-derived geography as exact when ambiguous.
- Allowing suppressed, blank, or low-confidence data to produce a green verdict.

## Review Checklist

- [ ] Every table and volume has a group or service-principal owner.
- [ ] Grants are group/service-principal based, not individual-user based.
- [ ] App identity has read-only access to cached gold outputs.
- [ ] Source objects are tagged with source, sensitivity, owner, and geo grain.
- [ ] Workspace-catalog binding is documented for non-dev targets.
- [ ] System tables or lineage can answer what produced each verdict.
- [ ] Gold outputs include enough caveats to explain uncertainty honestly.
