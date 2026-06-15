# Diagrams

These diagrams are version-controlled Mermaid diagrams so they render in GitHub and remain reviewable with the code.

## Table of Contents

- [Diagrams](#diagrams)
  - [Table of Contents](#table-of-contents)
  - [System Overview](#system-overview)
  - [Demo Flow](#demo-flow)
  - [PIN Readiness Decision](#pin-readiness-decision)

## System Overview

```mermaid
flowchart LR
  subgraph source [Public Sources]
    PincodeCsv["India Post PIN Code CSV"]
    NfhsCsv["NFHS-5 District CSV"]
  end

  subgraph bundle [Databricks Bundle]
    BronzeNotebook["01 Ingest Bronze"]
    SilverNotebook["02 Build Silver"]
    GoldNotebook["03 Build Gold"]
    DemoNotebook["04 Demo Queries"]
  end

  subgraph tables [Unity Catalog Delta Tables]
    BronzeTables["Bronze Raw Tables"]
    SilverTables["Silver Readiness Tables"]
    GoldTables["Gold Planning Tables"]
    QualityChecks["pipeline_quality_checks"]
  end

  PincodeCsv --> BronzeNotebook
  NfhsCsv --> BronzeNotebook
  BronzeNotebook --> BronzeTables
  BronzeTables --> SilverNotebook
  SilverNotebook --> SilverTables
  SilverNotebook --> QualityChecks
  SilverTables --> GoldNotebook
  GoldNotebook --> GoldTables
  GoldTables --> DemoNotebook
```

## Demo Flow

```mermaid
sequenceDiagram
  autonumber
  participant Judge
  participant Notebook as Databricks Notebook
  participant Tables as Gold Tables
  participant Agent as Planning Assistant

  Judge->>Notebook: Open demo queries
  Notebook->>Tables: Read district readiness outputs
  Tables-->>Notebook: Return rankings, ambiguity, and caution flags
  Notebook-->>Judge: Show readiness scorecards
  Judge->>Agent: Ask which districts need review
  Agent->>Tables: Use only gold tables
  Tables-->>Agent: Return grounded evidence
  Agent-->>Judge: Explain evidence, uncertainty, and next validation step
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
