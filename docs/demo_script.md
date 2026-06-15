# Demo Script

Use this as a short narrative for judges, teammates, or a Databricks booth walkthrough.

## Table of Contents

- [Opening](#opening)
- [Walkthrough](#walkthrough)
- [Suggested Judge Story](#suggested-judge-story)
- [Agent Prompt](#agent-prompt)
- [Strong Closing](#strong-closing)

## Opening

We are [Vibhu Ganesan](https://www.linkedin.com/in/vibhu-g-83313723) and [Devesh Padmanabhan](https://www.linkedin.com/in/deveshpa/). We are solving Problem 4, Data Readiness Desk: what must be fixed before planning can trust it?

This work is for the [Databricks Apps & Agents for Good Hackathon 2026](https://developers.databricks.com/hackathon/apps-agents-for-good-2026).

This project enriches healthcare facility planning in India with two public datasets: India Post postal geography and NFHS-5 district health indicators.

The key challenge is that neither dataset should be joined naively. Postal PIN codes are post-office grain and can map to multiple districts or states. NFHS values can be suppressed or based on small samples. The pipeline makes those caveats visible instead of hiding them.

## Walkthrough

1. Show [README.md](../README.md) and the medallion architecture diagram.
1. Open [notebooks/01_ingest_bronze.py](../notebooks/01_ingest_bronze.py) and show CSV ingestion from a Unity Catalog Volume.
1. Open [notebooks/02_build_silver.py](../notebooks/02_build_silver.py) and highlight:
   - PIN lookup aggregation
   - `is_geography_ambiguous`
   - NFHS suppressed-value and low-sample flags
1. Open [notebooks/03_build_gold.py](../notebooks/03_build_gold.py) and show:
   - `gold_district_health_context`
   - `gold_pincode_health_enrichment`
   - `gold_underserved_district_candidates`
1. Run [notebooks/04_demo_queries.py](../notebooks/04_demo_queries.py) and show:
   - Top underserved district candidates
   - Ambiguous PIN code examples
   - Match-status distribution
   - Data caution counts

## Suggested Judge Story

Most quick demos enrich facility data with postal codes directly. This project shows why that can be wrong. A PIN code can fan out to multiple post offices and administrative regions, so the pipeline creates a join-safe lookup and carries match-status flags into gold outputs.

The health indicators are also treated carefully. Suppressed NFHS values become null, not zero. Low-sample estimates are parsed but flagged. This means the downstream agent or dashboard can explain not only what it found, but how confident the data is.

## Agent Prompt

Use the printed prompt from [notebooks/04_demo_queries.py](../notebooks/04_demo_queries.py) with a Databricks assistant or app-layer agent.

Expected answer qualities:

- Uses only gold tables.
- Mentions data cautions.
- Avoids exact claims from ambiguous PIN matches.
- Recommends spatial validation when facility coordinates exist.

## Strong Closing

The value is not just another table. The value is a governed enrichment pattern that helps analysts combine public health context with facility data while preserving uncertainty. That matters for healthcare planning because false precision can send attention to the wrong place.
