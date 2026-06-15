# Decision Log

This log captures decisions that future engineers should understand before changing the pipeline.

## Table of Contents

- [Use Databricks Bundle For Deployment](#use-databricks-bundle-for-deployment)
- [Treat PIN Geography As A Readiness Signal](#treat-pin-geography-as-a-readiness-signal)
- [Preserve NFHS Suppression And Low-Sample Flags](#preserve-nfhs-suppression-and-low-sample-flags)
- [Keep Raw Data Out Of Git](#keep-raw-data-out-of-git)
- [Use Mermaid Diagrams](#use-mermaid-diagrams)

## Use Databricks Bundle For Deployment

Decision: manage jobs and notebooks through [databricks.yml](../databricks.yml).

Why it adds value:

- Keeps deployable Databricks resources tied to a Git commit.
- Lets CI validate the bundle before anyone deploys.
- Makes dev, staging, and prod targets explicit.

## Treat PIN Geography As A Readiness Signal

Decision: publish `silver_pincode_lookup` as one row per PIN and flag ambiguous geography.

Why it adds value:

- Prevents row fanout when enriching facility records.
- Makes uncertainty visible to dashboards and agents.
- Gives planners a review queue instead of false precision.

## Preserve NFHS Suppression And Low-Sample Flags

Decision: parse `*` as null and parenthesized values as low-sample estimates.

Why it adds value:

- Avoids treating unavailable indicators as zero.
- Lets agentic explanations cite data cautions.
- Keeps scoring exploratory rather than pretending to be authoritative.

## Keep Raw Data Out Of Git

Decision: source files live in Unity Catalog Volumes or documented public sources, not in the repository.

Why it adds value:

- Keeps the public repo small and shareable.
- Avoids accidental redistribution of raw operational extracts.
- Encourages tests to use small, license-safe fixtures.

## Use Mermaid Diagrams

Decision: use Mermaid diagrams in Markdown instead of a binary drawing artifact.

Why it adds value:

- Diagrams render in GitHub.
- Changes are reviewable in pull requests.
- Engineers can update diagrams with the same workflow as code.
