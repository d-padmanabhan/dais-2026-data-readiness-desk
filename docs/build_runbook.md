# Data Readiness Desk Build Runbook

> [!NOTE]
> Companion to [Data Readiness Desk Requirements](requirements.md). Ordered, executable steps for a coding agent or solo CLI build on Databricks Free Edition.

> [!IMPORTANT]
> Quota rule: compute every score once into a cached gold table. The app and demo only read cached outputs. Never recompute or train live.

## Table of Contents

- [Phase 0 - Local Setup](#phase-0---local-setup)
- [Phase 1 - Provision Unity Catalog](#phase-1---provision-unity-catalog)
- [Phase 2 - Bronze Ingest](#phase-2---bronze-ingest)
- [Phase 3 - Silver Clean Normalize Resolve Geography](#phase-3---silver-clean-normalize-resolve-geography)
- [Phase 4 - AutoML Classifier](#phase-4---automl-classifier)
- [Phase 5 - Gold Score Everything](#phase-5---gold-score-everything)
- [Phase 6 - Streamlit App](#phase-6---streamlit-app)
- [Phase 7 - Deploy And Dry Run](#phase-7---deploy-and-dry-run)
- [Time Budget](#time-budget)
- [Quota-Safety Checklist](#quota-safety-checklist)

## Phase 0 - Local Setup

```bash
# Databricks CLI v0.250.0+ required for apps + bundles
databricks -v
# install/update if needed: https://docs.databricks.com/dev-tools/cli/install
databricks auth login --host https://<your-free-edition>.cloud.databricks.com
# pick a profile name, e.g. DEFAULT; verify:
databricks current-user me
```

Project skeleton:
```bash
mkdir drd && cd drd
mkdir -p notebooks app data
# Catalog/schema we'll use throughout:
#   catalog: drd   schema: gold (+ bronze, silver)
```

**Owner split (from spec section 3):** Engineer runs Phases 1-5 (data + model). You run Phases 6-7 (app + demo). Phases can overlap once silver lands.


## Phase 1 - Provision Unity Catalog

Run in a notebook (`notebooks/00_setup.py`) on serverless:

```sql
CREATE CATALOG IF NOT EXISTS drd;
CREATE SCHEMA IF NOT EXISTS drd.bronze;
CREATE SCHEMA IF NOT EXISTS drd.silver;
CREATE SCHEMA IF NOT EXISTS drd.gold;
CREATE VOLUME IF NOT EXISTS drd.bronze.files;  -- for uploaded files
```

Upload the file-based sources to the volume (UI: Catalog > drd.bronze.files > Upload, or CLI):
```bash
databricks fs cp data/Facilities.xlsx dbfs:/Volumes/drd/bronze/files/ --profile DEFAULT
databricks fs cp data/india_post_pincode_directory.csv dbfs:/Volumes/drd/bronze/files/
databricks fs cp data/hmis_2019_20_slice.csv dbfs:/Volumes/drd/bronze/files/
databricks fs cp data/srs_2020_state.csv dbfs:/Volumes/drd/bronze/files/
# district boundary polygons (geojson) too
databricks fs cp data/india_districts.geojson dbfs:/Volumes/drd/bronze/files/
```
NFHS-5 is already a provided table - just note its full name for joins.


## Phase 2 - Bronze Ingest

`notebooks/01_bronze.py`. Land everything raw, no cleaning yet.

```python
import pandas as pd
V = "/Volumes/drd/bronze/files"

# Facilities (100 rows) - pandas is fine at this size
fac = pd.read_excel(f"{V}/Facilities.xlsx")
spark.createDataFrame(fac).write.mode("overwrite").saveAsTable("drd.bronze.facilities")

for name, fn in [("pincode","india_post_pincode_directory.csv"),
                 ("hmis","hmis_2019_20_slice.csv"),
                 ("srs","srs_2020_state.csv")]:
    (spark.read.option("header",True).option("inferSchema",True)
        .csv(f"{V}/{fn}")
        .write.mode("overwrite").saveAsTable(f"drd.bronze.{name}"))
```

**Quota note:** read once, write Delta, never re-read raw in later phases.


## Phase 3 - Silver Clean Normalize Resolve Geography

`notebooks/02_silver.py`. This is where the denominator + grain discipline lives.

### Facilities Geography Resolution
```python
# point-in-polygon: assign each facility to a district from coordinates
# (use geopandas; sjoin facility points to drd.bronze districts geojson)
import geopandas as gpd
fac = spark.table("drd.bronze.facilities").toPandas()
gdf = gpd.GeoDataFrame(fac, geometry=gpd.points_from_xy(fac.longitude, fac.latitude), crs="EPSG:4326")
dist = gpd.read_file(f"{V}/india_districts.geojson")[["district","state","geometry"]]
joined = gpd.sjoin(gdf, dist, how="left", predicate="within")
# conflict flag: stated state vs polygon state (spec section 5.1)
joined["geo_conflict"] = joined["address_stateOrRegion"].str.lower() != joined["state"].str.lower()
# resolution rule: valid coords exist here (100% fill) -> polygon wins, conflict = fixable amber
spark.createDataFrame(joined.drop(columns="geometry")).write.mode("overwrite").saveAsTable("drd.silver.facilities_geo")
```

### NFHS-5 Missingness Parsing
```python
# CRITICAL: distinguish * (suppressed), (parenthesized) low-conf, blank
# produce per-indicator: value (float|null) + quality_flag in {ok, suppressed, lowconf, blank}
# snake_case the long column names while here
```

### HMIS Denominator Normalization
```python
# HMIS numerator = facility activity counts; convert to a RATE comparable to NFHS %
# institutional delivery: deliveries_in_facility / expected_births
#   expected_births = district_population * crude_birth_rate / 1000
# Document the denominator formula in a comment + surface it in the app's why-panel.
```

### District Name Harmonization
```python
# NFHS, HMIS, polygons all spell districts differently.
# Prefer the polygon-derived district key everywhere; map NFHS/HMIS names to it.
# Keep an explicit `geo_grain` column on every silver table: 'point' | 'district' | 'state'.
```


## Phase 4 - AutoML Classifier

`notebooks/03_model.py`.

```python
from databricks import automl
# training set: districts where NFHS & HMIS AGREE on institutional delivery
# features: district health/demographic context (NFHS indicator group cols)
# label: HMIS-reported coverage (regression) OR agree/disagree (classification)
train = spark.table("drd.silver.disease_training")  # built in 3c
summary = automl.regress(train, target_col="hmis_delivery_rate", timeout_minutes=15)
# register the best model
import mlflow
mlflow.register_model(summary.best_trial.model_path, "drd.gold.coverage_predictor")
```
Then **batch-score offline** and save predictions - no live inference in demo:
```python
preds = ...  # model.predict over all districts incl. suppressed-NFHS ones
preds.write.mode("overwrite").saveAsTable("drd.gold.coverage_predictions")
# anomaly flag: actual NFHS-HMIS gap exceeds predicted expected gap
```
**Fallback if behind:** skip AutoML, write a static `coverage_predictions` table from a simple rule. Still satisfies "model on platform" as architecture; note it in the pitch.


## Phase 5 - Gold Score Everything

`notebooks/04_gold_scores.py`. Encodes spec section 4. Pre-compute ALL verdicts.

```python
CFG = dict(  # spec section 11 - single tunable block
  BAND_GREEN_MIN=0.85, BAND_AMBER_MIN=0.60,
  DELIV_GAP_GREEN=8, DELIV_GAP_RED=20,
  IMMUN_GAP_GREEN=15, IMMUN_GAP_RED=35,
  ANC_GAP_GREEN=12, ANC_GAP_RED=28,
  SRS_WEAK_WEIGHT=0.5, EXTRACTED_CONFIDENCE=0.6,
)

# Per entity (facility / district+indicator), compute each dimension 0-1, then:
#   numeric_score = weighted average of applicable dimensions
#   band = weakest-link cap, bounded by BAND cutoffs
#   HARD RULE: any suppressed/lowconf/blank -> band capped at amber (never green)
#   reason = name of the binding (worst) dimension, one line
# Write gold tables the app reads:
#   drd.gold.facility_verdicts
#   drd.gold.district_verdicts
#   drd.gold.fix_ranking
```

### Facility Capability Extraction
```sql
-- ai_extract is a GA built-in; no endpoint to provision
CREATE OR REPLACE TABLE drd.gold.facility_caps AS
SELECT unique_id,
       ai_extract(capability, ARRAY('bed_count','doctor_count','has_24x7_er','has_nicu','accreditation')) AS extracted
FROM drd.silver.facilities_geo;
-- extracted values get EXTRACTED_CONFIDENCE (0.6) weight, tagged provenance='inferred'
```

### Fix Ranking
```python
# rank = (est_score_lift_if_fixed) * (district_burden * population_affected)
# missing-data fixes on HIGH-WEIGHT fields get a priority boost
# burden fallback: if district burden suppressed -> state burden, flagged weak
```

**Verify before moving on:**
```python
for t in ["facility_verdicts","district_verdicts","fix_ranking"]:
    df = spark.table(f"drd.gold.{t}")
    print(t, df.count())
    df.filter("band='green'").show(3)  # sanity: greens look right, no green on suppressed
```


## Phase 6 - Streamlit App

Project files in `app/`:

```
app/
  app.py
  app.yaml
  requirements.txt
```

`app/app.yaml`:
```yaml
command: ['streamlit', 'run', 'app.py']
env:
  - name: 'DATABRICKS_WAREHOUSE_ID'
    value: '<your-sql-warehouse-id>'
  - name: 'STREAMLIT_GATHER_USAGE_STATS'
    value: 'false'
```

`app/requirements.txt`:
```
streamlit
databricks-sql-connector
pydeck
```

`app/app.py` skeleton (READS cached gold only):
```python
import streamlit as st
from databricks import sql
import os

st.title("Data Readiness Desk")
st.caption("Can I trust the data for: ___?")
lens = st.radio("Lens", ["Location","Disease/Condition","Facility"], horizontal=True)
q = st.text_input("Place, condition, or facility")

def run(query):  # reads gold tables; no recompute
    with sql.connect(server_hostname=os.environ["DATABRICKS_HOST"],
                     http_path=f"/sql/1.0/warehouses/{os.environ['DATABRICKS_WAREHOUSE_ID']}",
                     access_token=os.environ["DATABRICKS_TOKEN"]) as c:
        return c.cursor().execute(query).fetchall()

if q:
    # 1) verdict card: band emoji + numeric score + one-line binding-dimension reason
    # 2) pydeck map colored by verdict
    # 3) ranked fix panel (fix + est lift + impact weight)
    # 4) "Apply fix" button -> read the pre-computed AFTER row -> show delta
    ...
```

**Genie (spec section 1 limits):** wire the search box to a Genie space ONLY for NL parsing of the user's question, user-initiated, and cache the parse. Do not call Genie on every render. If Genie quota is a worry, ship a simple keyword parser for the demo and mention Genie as the production interface.

**Before/after demo trick:** pre-compute both the current verdict AND the post-fix verdict in gold (two rows / a `state` column). "Apply fix" just swaps which row is shown - zero compute, instant, quota-safe.


## Phase 7 - Deploy And Dry Run

```bash
# create the app first (CLI), then deploy source
databricks apps create drd-desk --profile DEFAULT
databricks sync ./app /Workspace/Users/<you>/drd-app --profile DEFAULT
databricks apps deploy drd-desk \
  --source-code-path /Workspace/Users/<you>/drd-app --profile DEFAULT
# open the app URL from the overview page; check Logs tab if it doesn't start
```

Dry run against acceptance criteria (spec section 10): location scores 100 facilities PASS - disease reconciles ≥1 district w/ denominator explanation PASS - model predictions table present PASS - ai_extract tagged partial-confidence PASS - verdict card shows band+number+reason PASS - ranked fixes render PASS - one before/after works PASS - zero live compute PASS.


## Time budget (6 hrs, 2 builders)

| Phase | Engineer | You |
|-------|----------|-----|
| 0-1 setup/catalog | H1 | (help / start app skeleton) |
| 2-3 bronze/silver | H1-H2 | app shell + verdict card layout |
| 4 AutoML | H3 | map view |
| 5 gold scores + ai_extract | H3-H4 | fix panel + before/after |
| 6 app wiring | (support) | H5 |
| 7 deploy + dry run | H6 | H6 |

**Cut-order if behind (spec section 3):** ANC indicator -> SRS anchor -> immunization showcase -> AutoML (swap to static table). NEVER cut: location lens, institutional-delivery corroboration, one before/after fix.


## Quota-Safety Checklist
- [ ] All verdicts pre-computed to gold; app issues SELECTs only.
- [ ] Model trained once, predictions batch-scored to a table.
- [ ] Genie calls user-initiated + cached (or keyword parser for demo).
- [ ] No `.write` or training cells run during the live demo.
- [ ] Data slices small (100 facilities, 2-3 HMIS states).
- [ ] One serverless SQL warehouse, started before demo, not spun per query.
