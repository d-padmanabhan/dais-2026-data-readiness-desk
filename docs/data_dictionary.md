# Data Dictionary

This document summarizes the input files and the Delta tables produced by the pipeline.

## Table of Contents

- [Source Files](#source-files)
- [Bronze Tables](#bronze-tables)
- [Silver Tables](#silver-tables)
- [Gold Tables](#gold-tables)

## Source Files

### India Post PIN Code Directory

Filename: `india_post_pincode_directory.csv`

Expected source columns:

- `circlename`
- `regionname`
- `divisionname`
- `officename`
- `pincode`
- `officetype`
- `delivery`
- `district`
- `statename`
- `latitude`
- `longitude`

Row grain: post office.

Important implication: one PIN code can appear on multiple rows and can map to multiple districts or states.

### NFHS-5 District Health Indicators

Filename: `nfhs5_district_health_indicators.csv`

Expected content:

- One row per district fact sheet record.
- State and district geography columns.
- Human-readable indicator columns covering household conditions, maternal health, child health, vaccination, nutrition, anaemia, non-communicable disease, cancer screening, tobacco, and alcohol.

Important implication: indicator names are long and may vary slightly between extracts. The pipeline normalizes column names to snake_case.

### HMIS 2019-20 Slice

Filename: `hmis_2019_20_slice.csv`

Expected source columns:

- `State`
- `S.No.`
- `Parameters`
- `Type`
- Monthly measure columns such as `April - Total [(A+B) or (C+D)]`

Row grain: state + parameter + reporting type, with one value per month/value-type column.

Important implication: the currently uploaded file is state-grain and encoded as `cp1252`. District-level disease reconciliation requires a district-grain extract or an explicit state-grain fallback.

## Bronze Tables

### `bronze_india_post_pincode_directory`

Raw India Post rows plus ingestion metadata.

Metadata columns:

- `_source_file`
- `_ingested_at_utc`

### `bronze_nfhs5_district_health_indicators`

Raw NFHS rows plus ingestion metadata.

Metadata columns:

- `_source_file`
- `_ingested_at_utc`

### `bronze_hmis_2019_20_slice`

Raw HMIS rows plus ingestion metadata.

Metadata columns:

- `_source_file`
- `_ingested_at_utc`

## Silver Tables

### `silver_pincode_post_offices`

Cleaned post-office rows.

Key added or normalized columns:

- `pincode`: 6-character string
- `district_normalized`
- `state_normalized`
- `latitude`: double, null when unavailable
- `longitude`: double, null when unavailable
- `has_coordinates`

### `silver_pincode_lookup`

One row per PIN code for safe joins.

Key columns:

- `pincode`
- `post_office_count`
- `district_count`
- `state_count`
- `districts_normalized`
- `states_normalized`
- `district_names`
- `state_names`
- `geocoded_office_count`
- `is_geography_ambiguous`
- `representative_district_normalized`
- `representative_state_normalized`

### `silver_nfhs_indicator_quality_long`

Long-form NFHS indicator cells with parsing and quality flags.

Key columns:

- `state_name`
- `district_name`
- `state_normalized`
- `district_normalized`
- `indicator_name`
- `raw_value`
- `is_suppressed`
- `is_low_sample_estimate`
- `value`

### `silver_nfhs5_district_health_indicators`

Wide district-level NFHS table with numeric indicator values and row-level quality counts.

Key columns:

- `state_name`
- `district_name`
- `state_normalized`
- `district_normalized`
- One numeric column per normalized NFHS indicator
- `indicator_cell_count`
- `suppressed_indicator_count`
- `low_sample_estimate_count`

### `silver_hmis_2019_20_long`

Long-form HMIS state-grain measurements.

Key columns:

- `state_name`
- `state_normalized`
- `serial_number`
- `parameter`
- `reporting_type`
- `source_column`
- `month`
- `value_type`
- `raw_value`
- `value`
- `is_invalid_numeric`
- `geo_grain`
- `source_period`
- `_recorded_at_utc`

### `pipeline_quality_checks`

Run-level readiness checks emitted by the silver pipeline.

Key columns:

- `check_name`
- `status`
- `observed_value`
- `_recorded_at_utc`

## Gold Tables

### `gold_district_health_context`

District-level public health context joined to postal coverage summaries.

Use this for district dashboards, ranking, and planning narratives.

### `gold_pincode_health_enrichment`

One row per PIN code with representative district health context where the PIN geography is not ambiguous.

Key columns:

- `pincode`
- `is_geography_ambiguous`
- `match_status`
- `nfhs_*` fields for matched health indicators

Match statuses:

- `matched`
- `ambiguous_pin_geography`
- `no_representative_district`
- `unmatched_nfhs_district`

### `gold_underserved_district_candidates`

District-level exploratory ranking table for hackathon demos.

Key columns:

- `state_name`
- `district_name`
- `demand_side_need_score`
- `health_insurance_percent`
- `institutional_delivery_percent`
- `women_anaemia_percent`
- `child_stunting_percent`
- `post_office_count`
- `data_caution`
