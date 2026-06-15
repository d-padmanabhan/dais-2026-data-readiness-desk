# Data Readiness Desk Requirements

> [!NOTE]
> For Databricks coding agents and CLI builds. Hackathon: Databricks for Good - Healthcare. Dataset: Virtue Foundation India facilities plus NFHS-5, HMIS, India Post PIN, and SRS. Track: Data Readiness Desk.

> [!IMPORTANT]
> Build target: working core plus stubbed edges in approximately 6 hours with 2 builders.

## Table of Contents

- [Product Definition](#product-definition)
- [Environment And Platform Constraints](#environment-and-platform-constraints)
- [Data Sources And Load State](#data-sources-and-load-state)
- [Scope](#scope)
- [Scoring Engine](#scoring-engine)
- [Lens Specifications](#lens-specifications)
- [Model Requirement](#model-requirement)
- [GenAI Requirement](#genai-requirement)
- [Databricks Product Mapping](#databricks-product-mapping)
- [UI Requirements](#ui-requirements)
- [Acceptance Criteria](#acceptance-criteria)
- [Tunable Constants](#tunable-constants)
- [Explicit Non-Goals And Caveats](#explicit-non-goals-and-caveats)

## Product Definition

A health planner asks **"Can I trust the data for: ___?"** (a place, a condition, or a facility). The app returns a **Trust Verdict** (Green/Amber/Red + numeric score + one-line reason) and a **ranked list of high-impact fixes**, then re-scores to prove a fix landed.

The app answers *"can I act on this number,"* not *"is this district healthy."* This distinction is the product.


## Environment And Platform Constraints

- **Databricks Free Edition** (serverless successor to Community Edition). Supports SQL/Python, Genie, Model Serving, AI Functions, Databricks Apps.
- **FAIR-USAGE CLIFF:** exceeding quota shuts down workspace compute for the rest of the day/month. Therefore:
  - All datasets are **small slices**. No full-nation ingestion.
  - **Pre-compute and cache** all scores into a Delta/Lakebase table. The app reads cached results; it does **not** recompute on user interaction.
  - No live model training during the demo - train once, register, load.
- **Genie limits:** ~5 questions/min (API), ~80-100/month free. Genie calls must be **user-initiated and cached**; never call Genie on keystroke or page-load loops.
- **UI:** Databricks Apps, **Streamlit** (simplest for a verdict-card + map UI).
- **Commercial use prohibited** on Free Edition - this is a demo/learning build only.


## Data Sources And Load State

| Source | Grain | Load state | Role |
|--------|-------|-----------|------|
| Virtue Foundation facilities | point | **file** (Facilities.xlsx, 100 rows) | facility lens + location lens inputs |
| India Post PIN directory | PIN/post-office | file (data.gov.in) | location corroboration |
| District boundary polygons | district | file (geoBoundaries/DataMeet) | point-in-polygon -> district |
| NFHS-5 district indicators | district | **table** (provided) | disease lens (survey side) |
| HMIS 2019-20 slice | district | file (data.gov.in, 2-3 states) | disease lens (admin side) |
| SRS 2020 | **state** | file (censusindia) | weak corroboration anchor |

**Mixed load:** agent must handle both pre-loaded tables and file ingestion into a medallion layout (bronze -> silver -> gold).

**Known facts about the facility slice (inspected - do not re-derive):**
- 100 rows, 51 cols, all India, 24 states.
- Coordinates clean: 0 null lat/long, 0 zero-island, valid India ranges.
- `cluster_id` is **unique per row** - dedup is pre-resolved. Do NOT build entity resolution; treat as given.
- Fill rates that matter: latitude/longitude/address/zip/name = 100%; `description`/`specialties`/`capability`/`procedure`/`equipment` = 99-100%; **numberDoctors 26%, capacity 10%, yearEstablished 36%, recency_of_page_update 18%**; `area`/`countries`/`acceptsVolunteers` = **0% (dead columns - ignore)**.
- `capability` = 99%-full JSON list of free-text claims (beds, doctors, 24/7 ER, NICU, accreditation) -> input to `ai_extract`.


## Scope

| Lens | Status | Notes |
|------|--------|-------|
| **Location** | BUILD FULLY | coords + PIN + polygons |
| **Disease / Condition** | BUILD FULLY | NFHS-5 <-> HMIS + SRS anchor - the engine |
| **Facility** | DEMO STUB | real fields, shown on the 100-row slice |

Protect-first if behind: location lens + institutional-delivery corroboration + one before/after fix. One lens fully working beats three half-wired.


## Scoring Engine

### Governing Philosophy
- **Specificity over sensitivity.** False trust (confident-but-wrong) is the worst outcome.
- **Missing data is the cardinal sin.**
- **Conservative under uncertainty** - thin evidence flags down.
- **HARD RULE: absent/suppressed/low-confidence data can never yield green.** Amber is the ceiling for any value we can't fully stand behind.
- **The Desk never picks a winner between conflicting sources.** It flags divergence and explains it; arbitration is out of scope.

### Dimensions

| Dimension | Applies to | Definition |
|-----------|-----------|------------|
| Completeness | all | required fields present for this entity/question |
| Geographic grain | all | level the answer is actually at; cross-grain comparison flagged |
| Corroboration | disease, location | independent source agreement |
| Reconcilability | disease | can the sources even be compared (definition/denominator match) |
| Provenance confidence | facility | structured field vs. extracted-from-text vs. absent |
| Freshness | disease | source staleness vs. its question (**dropped for facility v1** - too sparse) |

### Missingness Handling

| Marker | Meaning | Verdict effect |
|--------|---------|----------------|
| `*` suppressed | small sample masked | **amber cap** + caveat |
| `(parenthesized)` | 25-49 unweighted cases | **amber cap - never green** |
| blank / NULL | no value | **amber cap** for color, AND forces missingness flag + makes "acquire this data" the #1 fix **if field is high-weight** |

All three land amber for *color*; blank is distinguished only in the *fix ranking* (per section 4.6), honoring "missing = cardinal sin" without over-penalizing color.

### Roll-Up Math

- **Numeric score** (shown under the band) = **weighted average** of applicable dimensions. Smooth, tunable.
- **Band** (Green/Amber/Red) = **weakest-link capped**: the worst dimension dictates the ceiling, then bounded by the numeric cutoffs.
- Result: a district can have a respectable average (e.g. 0.72) but display amber because one binding dimension (e.g. corroboration) is red. *Number = overall quality; color = binding constraint.*
- No standalone hard vetoes beyond the weakest-link cap and the section 4.1 absent-data rule.

**Default band cutoffs (TUNABLE constants):** green >= 0.85 - amber 0.60-0.84 - red < 0.60. (Strict, per conservative posture.)

### Corroboration Bands

Divergence ≠ error (structural denominator differences). Tolerance widens with reconcilability:

| Indicator | Reconcilability | Corroborated (green) | Amber | Red |
|-----------|----------------|---------------------|-------|-----|
| Institutional delivery | green clean | gap < 8 pts | 8-20 | > 20 |
| Full immunization | amber denom-fragile | < 15 | 15-35 | > 35 |
| ANC 4+ visits | amber ratio-inflated | < 12 | 12-28 | > 28 |
| Anaemia | red contested method | - burden-weight ONLY, never a corroboration target |
| C-section | red diverges | - skip |

- **SRS (state) corroborating a district value = weak signal:** ~0.5 weight of a true district-level match; can nudge up but cannot alone produce green. Grain mismatch shown in caveat.
- **On sharp divergence:** flag both, show the denominator explanation, recommend verification. Never pick a side.

### Fix Ranking

**rank score = (estimated score lift if fixed) x (district health burden x population affected)**

- Burden x population = the **"for good" multiplier** - repairs in high-burden, high-population districts rise to the top.
- **Missing-data fixes on HIGH-WEIGHT fields get a priority boost** (cardinal-sin rule, applied selectively - low-weight missing fields do NOT jump the queue).
- **Burden fallback:** if a district's NFHS burden is itself suppressed, use **state-level burden as a flagged weak proxy** - never silently drop the district from ranking.

### Provenance Confidence
- Structured field present = full confidence (1.0).
- Value recovered by `ai_extract` from `capability` text = **partial credit (0.6, TUNABLE)** + provenance tag.
- Absent = 0.
- Demo beat: "looks complete, but 4 of 6 capacity facts were inferred from marketing text -> amber, not green."


## Lens Specifications

### Location
**Q:** "Can I trust the location data for [facility/area]?"
- Completeness: lat/long + address + postcode present.
- Geocodability: coords valid, in-country, not 0/0.
- Resolvability: point-in-polygon -> district; cross-check vs. PIN directory.
- Corroboration: stated geography vs. PIN-directory vs. polygon result (**NOT** vs. HMIS).
- **Conflict rule (stated district ≠ polygon district):** if valid coords exist -> polygon wins, conflict logged as fixable address error (amber, fix = "correct stated district"); if coords absent/invalid -> unresolved -> red.
- District assignment method: **spatial join on coordinates (primary)**, name match fallback only.

### Disease Or Condition
**Q:** "Can I trust the [condition] data for [district]?"
- NFHS-5 (district) vs. HMIS 2019-20 (district, denominator-normalized) vs. SRS 2020 (state anchor, weak).
- Hero indicator: **institutional delivery**. Showcase: **immunization** (the famous ~94% vs ~56% gap -> red).
- Dimensions: corroboration (section 4.5), reconcilability, grain, completeness/suppression (section 4.3), survey-method flag (anaemia = contested).
- **Surface the WHY:** when sources disagree, display the denominator explanation ("HMIS uses expected births, NFHS uses surveyed births"). The denominator-normalization layer is a visible feature, not hidden plumbing.

### Facility
**Q:** "Can I trust the facility profile for [facility]?"
- Completeness over care-substance fields (surfaces the 10%/26%/36% gaps).
- `ai_extract` mines `capability` JSON -> structured attrs (beds, doctors, 24/7 ER, NICU, accreditation), tagged partial-confidence.
- **E2 consequence (state in pitch):** care-substance is both highest-weight AND sparsest -> most facilities correctly score amber/red. That's honesty, not failure.


## Model Requirement

- **Task:** binary/regression classifier on districts where NFHS & HMIS **agree** -> predict expected coverage where one source is suppressed/missing.
- **Use:** flag districts whose actual divergence exceeds prediction as anomalies (feeds corroboration dimension).
- **Tooling:** Databricks AutoML; train once, register to model registry, load cached. **No live training in demo.**
- If time-tight: pre-train, ship predictions as a static scored table (still satisfies "model on platform").


## GenAI Requirement
- **`ai_extract`** (GA) on `capability` free-text -> structured facility attributes. Built-in SQL AI function; no served endpoint to manage.
- Optionally `ai_classify` for facility-type normalization. Keep to built-ins for speed.


## Databricks Product Mapping

| Layer | Product |
|-------|---------|
| Storage + score history | **Lakebase** (enables before/after re-score) |
| Ingestion | Delta medallion (bronze->silver->gold) |
| GenAI extraction | **ai_extract / ai_classify** |
| Model | **AutoML** -> registry |
| Orchestration / fix engine | **Agent** (diagnose -> recommend -> re-score) |
| NL interface | **Genie** ("Can I trust the data for ___?") |
| Marketplace | published PIN + NFHS-5 (+ added HMIS/SRS) |
| UI | **Databricks Apps (Streamlit)** - verdict card + map + why-panel |


## UI Requirements

- **Input:** one search box + lens toggle (location / disease / facility). Genie powers NL parsing, user-initiated only.
- **Verdict card:** band (Green/Amber/Red) + numeric score + **one-line reason naming the binding dimension** (e.g. "Amber - corroboration: NFHS and HMIS disagree by 22 pts").
- **Map:** facilities/districts colored by verdict.
- **Fix panel:** ranked list, each row = fix + estimated score lift + impact weight.
- **Before/after:** apply a fix -> re-score -> show delta. The signature demo moment.
- All reads from cached gold table. No recompute on interaction.


## Acceptance Criteria

1. Location lens scores all 100 facilities end-to-end from cached table.
2. Disease lens reconciles NFHS<->HMIS institutional delivery for >=1 demo district, shows denominator explanation on divergence.
3. AutoML model trained, registered, predictions in scored table.
4. `ai_extract` produces structured attrs for >=1 facility, tagged partial-confidence.
5. Verdict card shows band + number + binding-dimension reason.
6. Ranked fix list renders with impact weighting.
7. One before/after re-score works live.
8. No live recompute / no live training during demo (quota safety).


## Tunable Constants

```
BAND_GREEN_MIN = 0.85
BAND_AMBER_MIN = 0.60
DELIV_GAP_GREEN = 8;  DELIV_GAP_RED = 20
IMMUN_GAP_GREEN = 15; IMMUN_GAP_RED = 35
ANC_GAP_GREEN = 12;   ANC_GAP_RED = 28
SRS_WEAK_WEIGHT = 0.5
EXTRACTED_CONFIDENCE = 0.6
# dimension weights per lens - default equal, tune in config
```


## Explicit Non-Goals And Caveats
- Not an analytics tool - does not declare which source is "true."
- Entity resolution NOT built (pre-resolved in slice) - claimed as architecture only.
- HMIS is a 2-3 state slice matched to NFHS-5's 2019-21 window - designed to scale, not scaled.
- Facility freshness deferred (data too sparse).
- 3 grains (point/district/state) - grain is an explicit field so the tool never silently compares levels.
