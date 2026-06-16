# Diagrams

These diagrams are version-controlled Mermaid diagrams so they render in GitHub and remain reviewable with the code.

## Table of Contents

- [Diagrams](#diagrams)
  - [Table of Contents](#table-of-contents)
  - [Target State Architecture](#target-state-architecture)
  - [Demo Flow](#demo-flow)
  - [Scoring Pipeline](#scoring-pipeline)
  - [PIN Readiness Decision](#pin-readiness-decision)

## Target State Architecture

```mermaid
flowchart LR
  subgraph users["1. Users And Demo Surface"]
    Planner["Health Planner<br/>Judge or demo user"]
    Browser["Browser<br/>Interactive app session"]
  end

  subgraph app["2. Free Databricks App Runtime"]
    ReactClient["React + Vite Client<br/>Verdict cards and tables"]
    NodeServer["Node.js Server<br/>Read-only API"]
    StatementApi["SQL Statement API<br/>Parameterized queries"]
  end

  subgraph access["3. Governance And Access"]
    ServicePrincipal["Service Principal OAuth<br/>CI and local automation"]
    UserGrant["Read Grant<br/>USE CATALOG, USE SCHEMA, SELECT"]
    Catalog["Unity Catalog<br/>data_readiness_desk"]
    PipelineSchema["Schema<br/>pipeline"]
    SourceVolume["Volume<br/>bronze.files"]
  end

  subgraph sources["4. Source Data"]
    FacilitiesTable["Shared Facilities Table<br/>Virtue Foundation dataset"]
    HmisCsv["HMIS 2019-20 CSV<br/>State-grain fallback"]
    SrsCsv["SRS 2020 State CSV"]
    BoundaryGeojson["India District GeoJSON"]
    PincodeCsv["India Post PIN CSV<br/>Optional"]
    NfhsSource["NFHS-5 District Data<br/>Optional table or file"]
  end

  subgraph bundle["5. Declarative Automation Bundle"]
    Preflight["00 Preflight<br/>Source and access checks"]
    BronzeNotebook["01 Ingest Bronze<br/>Raw Delta tables"]
    SilverNotebook["02 Build Silver<br/>Normalize and flag quality"]
    GoldNotebook["03 Build Gold<br/>Cached verdict outputs"]
    DemoNotebook["04 Demo Queries<br/>Smoke-test outputs"]
  end

  subgraph outputs["6. Medallion Outputs"]
    BronzeTables["Bronze Prefixed Tables<br/>source-aligned rows"]
    SilverTables["Silver Tables<br/>quality flags and normalized geography"]
    FacilityVerdicts["gold_facility_verdicts<br/>location and completeness trust"]
    HmisSummary["gold_hmis_state_indicator_summary<br/>state-grain caution"]
    QualityChecks["pipeline_quality_checks<br/>run health checks"]
    FutureGold["Future Gold Tables<br/>district verdicts and fix ranking"]
  end

  subgraph demo["7. Demo Guardrails"]
    CachedOnly["Cached outputs only"]
    ReadOnly["App is read-only"]
    NoLiveTraining["No live training or writes"]
    Uncertainty["Uncertainty is visible"]
  end

  Planner --> Browser
  Browser --> ReactClient
  ReactClient --> NodeServer
  NodeServer --> StatementApi
  StatementApi --> PipelineSchema

  ServicePrincipal --> Catalog
  UserGrant --> Catalog
  Catalog --> PipelineSchema
  Catalog --> SourceVolume

  HmisCsv --> SourceVolume
  SrsCsv --> SourceVolume
  BoundaryGeojson --> SourceVolume
  PincodeCsv -. when available .-> SourceVolume
  NfhsSource -. when available .-> BronzeNotebook
  FacilitiesTable --> BronzeNotebook
  SourceVolume --> Preflight
  FacilitiesTable --> Preflight
  Preflight --> BronzeNotebook
  BronzeNotebook --> BronzeTables
  BronzeTables --> SilverNotebook
  SilverNotebook --> SilverTables
  SilverNotebook --> QualityChecks
  SilverTables --> GoldNotebook
  GoldNotebook --> FacilityVerdicts
  GoldNotebook --> HmisSummary
  GoldNotebook -. planned .-> FutureGold
  FacilityVerdicts --> DemoNotebook
  HmisSummary --> DemoNotebook
  QualityChecks --> DemoNotebook
  FacilityVerdicts --> StatementApi
  HmisSummary --> StatementApi
  QualityChecks --> StatementApi

  FacilityVerdicts --> CachedOnly
  HmisSummary --> CachedOnly
  CachedOnly --> ReadOnly
  CachedOnly --> NoLiveTraining
  FacilityVerdicts --> Uncertainty
  HmisSummary --> Uncertainty
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
