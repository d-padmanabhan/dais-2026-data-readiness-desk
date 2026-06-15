# Data Quality Decisions

The source files are real-world public-sector datasets. This project favors transparent uncertainty over false precision.

## Table of Contents

- [PIN Code Directory](#pin-code-directory)
- [Coordinates](#coordinates)
- [NFHS-5 Indicators](#nfhs-5-indicators)
- [String Matching](#string-matching)
- [Demo Scoring](#demo-scoring)

## PIN Code Directory

The India Post file is post-office grain, not PIN-code grain. A single PIN can appear on multiple rows and can map to more than one district or state.

Handling rules:

- Keep post-office rows in `silver_pincode_post_offices`.
- Build one row per PIN in `silver_pincode_lookup`.
- Preserve `post_office_count`, `district_count`, `state_count`, `district_names`, and `state_names`.
- Set `is_geography_ambiguous` when a PIN maps to more than one normalized district or state.
- Only set representative district and state fields when geography is not ambiguous.
- Do not join facility records directly to post-office rows on `pincode`; use `silver_pincode_lookup` or a spatial join.

> [!CAUTION]
> A PIN-code match is an enrichment hint, not a verified administrative boundary assignment. Facilities with latitude and longitude should be assigned to districts by spatial point-in-polygon joins.

## Coordinates

The PIN code file includes latitude and longitude, but some rows use `NA`.

Handling rules:

- Convert `NA` latitude and longitude values to null.
- Add `has_coordinates` in `silver_pincode_post_offices`.
- Carry `geocoded_post_office_count` and `geocoded_post_office_ratio` to show coordinate coverage.

## NFHS-5 Indicators

The NFHS file contains long, human-readable column names and values that need interpretation.

Handling rules:

- Convert column names to snake_case.
- Normalize state and district strings for approximate joins.
- Treat `*` as unavailable and parse it as null.
- Parse parenthesized values such as `(29.5)` as numeric values and flag them as low-sample estimates.
- Preserve cell-level quality flags in `silver_nfhs_indicator_quality_long`.
- Publish numeric district indicators in `silver_nfhs5_district_health_indicators`.

> [!IMPORTANT]
> Suppressed or unavailable values are not zero. Any ranking or score should either exclude them or make the missingness visible.

## String Matching

State and district string normalization is useful for grouping and approximate joins, but it is not authoritative.

Normalization removes casing, punctuation, and spacing differences. It does not resolve historical boundary changes, transliteration differences, or district splits.

Recommended hierarchy for facility geography:

1. Use facility coordinates with district boundary polygons when coordinates are available.
1. Use verified facility district fields when available and standardized.
1. Use PIN-code lookup as a fallback with ambiguity flags.
1. Do not present fallback geography as exact.

## Demo Scoring

`gold_underserved_district_candidates` creates a lightweight demand-side score from available NFHS indicators. It is intended for exploration, not policy decisions.

The score combines:

- Higher women anaemia percentage
- Higher child stunting percentage
- Lower health insurance coverage
- Lower institutional delivery coverage

Missing metrics are handled conservatively so the demo remains runnable even if column names differ across NFHS extracts.
