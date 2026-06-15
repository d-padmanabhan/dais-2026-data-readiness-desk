# Data Folder

This folder holds local hackathon source files before they are copied into a Unity Catalog Volume for Databricks ingest.

## Source Files

Expected filenames:

- `Facilities.xlsx`
- `india_post_pincode_directory.csv`
- `hmis_2019_20_slice.csv`
- `srs_2020_state.csv`
- `india_districts.geojson`

NFHS-5 district health indicators may be available as a Databricks table instead of a local file. If a local CSV is used, document its filename in [docs/runbook.md](../docs/runbook.md) before ingesting it.

## HMIS Observations

The inspected `hmis_2019_20_slice.csv` file has these characteristics:

- Encoding: `cp1252`
- Shape: 20,368 rows and 69 columns
- Grain: state + parameter + type + monthly value columns
- Missing for district-level disease reconciliation: a district column or separate district-grain HMIS extract

## Handling Rules

- Keep these files as small hackathon slices. Do not ingest full-nation datasets unless the demo scope changes.
- Upload the files into the Unity Catalog Volume before running the notebooks.
- Do not train models or recompute scores from the app. All app screens should read cached gold outputs.
- Do not commit private credentials, tokens, or generated Databricks output here.

## Upload Command Template

```bash
databricks fs cp data/Facilities.xlsx dbfs:/Volumes/data_readiness_desk/bronze/files/
databricks fs cp data/india_post_pincode_directory.csv dbfs:/Volumes/data_readiness_desk/bronze/files/
databricks fs cp data/hmis_2019_20_slice.csv dbfs:/Volumes/data_readiness_desk/bronze/files/
databricks fs cp data/srs_2020_state.csv dbfs:/Volumes/data_readiness_desk/bronze/files/
databricks fs cp data/india_districts.geojson dbfs:/Volumes/data_readiness_desk/bronze/files/
```
