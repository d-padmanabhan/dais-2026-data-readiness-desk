# Data Folder

This folder holds local hackathon source files before they are copied into a Unity Catalog Volume for Databricks ingest.

## Source Files

Expected filenames:

- `india_post_pincode_directory.csv`
- `hmis_2019_20_slice.csv`
- `srs_2020_state.csv`
- `india_districts.geojson`

Facilities and NFHS-5 are available as Databricks shared tables rather than local files. If a local CSV is used later, document its filename in [docs/runbook.md](../docs/runbook.md) before ingesting it.

## HMIS Observations

The inspected `hmis_2019_20_slice.csv` file has these characteristics:

- Encoding: `cp1252`
- Shape: 20,368 rows and 69 columns
- Grain: state + parameter + type + monthly value columns
- Missing for district-level disease reconciliation: a district column or separate district-grain HMIS extract

## Build Or Fetch Local Sources

Generate SRS from the bulletin PDF:

```bash
just generate-srs
```

Fetch India district boundaries:

```bash
just fetch-boundaries
```

The boundary fetch script downloads `india_districts.geojson` from the [geohacker/india district GeoJSON source](https://github.com/geohacker/india/blob/master/district/india_district.geojson). The file uses `NAME_1` for state and `NAME_2` for district.

Fetch the India Post PIN directory through the official OGD API when you have an API key:

```bash
export DATA_GOV_API_KEY="<your-data-gov-api-key>"
just fetch-pincode
```

By default, the PIN fetch keeps only Tamil Nadu, Kerala, Telangana, Andhra Pradesh, Karnataka, Goa, and Maharashtra. Use `./scripts/fetch_pincode_directory.sh --all-states` if the demo scope expands.

If you do not have a data.gov.in API key, download the PIN directory CSV manually from the official Open Government Data portal and save it as `data/india_post_pincode_directory.csv`.

## Handling Rules

- Keep these files as small hackathon slices. Do not ingest full-nation datasets unless the demo scope changes.
- Upload the files into the Unity Catalog Volume before running the notebooks.
- Do not train models or recompute scores from the app. All app screens should read cached gold outputs.
- Do not commit private credentials, tokens, or generated Databricks output here.

## Upload Command Template

Preferred command:

```bash
./scripts/bootstrap_databricks_workspace.sh --warehouse-id <warehouse-id>
```

Equivalent manual commands:

```bash
databricks fs cp data/india_post_pincode_directory.csv dbfs:/Volumes/data_readiness_desk/bronze/files/
databricks fs cp data/hmis_2019_20_slice.csv dbfs:/Volumes/data_readiness_desk/bronze/files/
databricks fs cp data/srs_2020_state.csv dbfs:/Volumes/data_readiness_desk/bronze/files/
databricks fs cp data/india_districts.geojson dbfs:/Volumes/data_readiness_desk/bronze/files/
```
