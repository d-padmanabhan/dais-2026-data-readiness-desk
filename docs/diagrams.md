# Diagrams

These diagrams are version-controlled Mermaid diagrams so they render in GitHub and remain reviewable with the code.

## Table of Contents

- [Diagrams](#diagrams)
  - [Table of Contents](#table-of-contents)
  - [System Overview](#system-overview)
  - [Demo Flow](#demo-flow)
  - [Scoring Pipeline](#scoring-pipeline)
  - [PIN Readiness Decision](#pin-readiness-decision)

## System Overview

```mermaid
flowchart LR
  subgraph source [Source Files And Tables]
    FacilitiesTable["Shared Facilities Table"]
    PincodeCsv["India Post PIN Code CSV"]
    BoundaryGeojson["District Boundaries GeoJSON"]
    NfhsCsv["NFHS-5 District CSV"]
    HmisCsv["HMIS 2019-20 Slice"]
    SrsCsv["SRS 2020 State CSV"]
  end

  subgraph bundle [Databricks Bundle]
    BronzeNotebook["01 Ingest Bronze"]
    SilverNotebook["02 Build Silver"]
    ModelNotebook["03 Train Or Static Predictions"]
    GoldNotebook["03 Build Gold"]
    DemoNotebook["04 Demo Queries"]
    App["Free Databricks App<br/>React, Vite, Node.js"]
  end

  subgraph tables [Unity Catalog Delta Tables]
    BronzeTables["Bronze Raw Tables"]
    SilverTables["Silver Readiness Tables"]
    GoldTables["Gold Verdict Tables"]
    Lakebase["Lakebase Score History"]
    QualityChecks["pipeline_quality_checks"]
  end

  FacilitiesFile --> BronzeNotebook
  PincodeCsv --> BronzeNotebook
  BoundaryGeojson --> BronzeNotebook
  NfhsCsv --> BronzeNotebook
  HmisCsv --> BronzeNotebook
  SrsCsv --> BronzeNotebook
  BronzeNotebook --> BronzeTables
  BronzeTables --> SilverNotebook
  SilverNotebook --> SilverTables
  SilverNotebook --> QualityChecks
  SilverTables --> ModelNotebook
  ModelNotebook --> GoldNotebook
  GoldNotebook --> GoldTables
  GoldTables --> Lakebase
  GoldTables --> DemoNotebook
  GoldTables --> App
```

## Demo Flow

```mermaid
sequenceDiagram
  autonumber
  participant Judge
  participant App as Databricks App
  participant Tables as Gold Tables
  participant Agent as Planning Assistant

  Judge->>App: Ask "Can I trust the data for this?"
  App->>Tables: Read cached verdict and fix rows
  Tables-->>App: Return band, score, reason, fixes
  App-->>Judge: Show verdict card, map, and ranked fixes
  Judge->>Agent: Ask which districts need review
  Agent->>Tables: Use only gold tables
  Tables-->>Agent: Return grounded evidence
  Agent-->>Judge: Explain evidence, uncertainty, and next validation step
```

## Scoring Pipeline

```mermaid
flowchart TD
  SilverInputs["Silver tables with geo_grain and quality flags"] --> Dimensions["Dimension Scores"]
  Dimensions --> Completeness["Completeness"]
  Dimensions --> Grain["Geographic Grain"]
  Dimensions --> Corroboration["Corroboration"]
  Dimensions --> Reconcilability["Reconcilability"]
  Dimensions --> Provenance["Provenance Confidence"]
  Corroboration --> AutoMl["AutoML or Static Predictions"]
  Provenance --> AiExtract["ai_extract Facility Capabilities"]
  Completeness --> Verdict["Trust Verdict"]
  Grain --> Verdict
  Corroboration --> Verdict
  Reconcilability --> Verdict
  Provenance --> Verdict
  AutoMl --> Verdict
  AiExtract --> Verdict
  Verdict --> FixRanking["Ranked Fixes"]
  FixRanking --> BeforeAfter["Before And After Cached Rows"]
```

## PIN Readiness Decision

```mermaid
flowchart TD
  Facility["Facility record"] --> HasCoordinates{"Has coordinates?"}
  HasCoordinates -->|"Yes"| SpatialJoin["Assign district with boundary polygons"]
  HasCoordinates -->|"No"| HasPin{"Has PIN code?"}
  HasPin -->|"No"| ManualReview["Manual readiness review"]
  HasPin -->|"Yes"| PinLookup["Join to silver_pincode_lookup"]
  PinLookup --> IsAmbiguous{"PIN geography ambiguous?"}
  IsAmbiguous -->|"Yes"| Ambiguous["Use as hint only and flag for review"]
  IsAmbiguous -->|"No"| Enrich["Attach representative district health context"]
  SpatialJoin --> Enrich
```
