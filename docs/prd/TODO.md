# TODO

## Immediate Next Steps

- [x] Create or confirm the Unity Catalog structure.
  - [x] `data_readiness_desk`
  - [x] `data_readiness_desk.bronze`
  - [x] `data_readiness_desk.silver`
  - [x] `data_readiness_desk.gold`
  - [x] `/Volumes/data_readiness_desk/bronze/files/`

- [ ] Upload or copy source files into the Volume.
  - [x] `hmis_2019_20_slice.csv`
  - [ ] `Facilities.xlsx` when available
  - [ ] `india_post_pincode_directory.csv` when available
  - [ ] `srs_2020_state.csv` when available
  - [ ] `india_districts.geojson` when available

- [ ] Run bundle pipeline in dev.
  - [x] `databricks bundle validate --target dev`
  - [ ] `databricks bundle deploy --target dev`
  - [ ] `databricks bundle run virtue_foundation_pipeline --target dev`

- [ ] Validate currently implemented outputs.
  - [ ] `bronze_hmis_2019_20_slice`
  - [ ] `silver_hmis_2019_20_long`
  - [ ] `silver_hmis_2019_20_indicator_totals`
  - [ ] `gold_hmis_state_indicator_summary`

## Build Work

- [x] Add preflight validation task.
  - [x] Check source Volume exists.
  - [x] Check expected files exist.
  - [ ] Check NFHS table path is configured.
  - [x] Fail with clear messages before Spark reads.

- [ ] Build facility location lens.
  - [ ] Ingest `Facilities.xlsx`.
  - [ ] Ingest `india_districts.geojson`.
  - [ ] Build point-in-polygon assignment.
  - [ ] Publish `silver_facilities_geo`.
  - [ ] Publish `gold_facility_verdicts`.

- [ ] Build disease lens.
  - [ ] Decide whether state-grain HMIS fallback is acceptable for demo.
  - [ ] If district-grain HMIS arrives, update the contract and silver pipeline.
  - [ ] Add denominator normalization for institutional delivery.
  - [ ] Publish `gold_district_verdicts`.

- [ ] Build fix ranking.
  - [ ] Implement score lift calculation.
  - [ ] Add burden x affected population multiplier.
  - [ ] Publish `gold_fix_ranking`.

- [ ] Add GenAI extraction.
  - [ ] Add `ai_extract` over facility `capability`.
  - [ ] Tag extracted values as partial confidence.
  - [ ] Publish `gold_facility_caps`.

- [ ] Add model fallback.
  - [ ] Train AutoML once if time allows.
  - [ ] Otherwise publish static `gold_coverage_predictions`.
  - [ ] Document the fallback honestly in demo notes.

- [ ] Wire Streamlit app.
  - [ ] Read real cached gold tables.
  - [ ] Add verdict card.
  - [ ] Add map or table view.
  - [ ] Add ranked fixes.
  - [ ] Add before/after toggle from cached rows.
  - [ ] Enforce read-only, gold-only queries.

## Demo Prep

- [ ] Pick one strong story.
  - [ ] State-grain HMIS fallback, if only HMIS is available.
  - [ ] Facility location trust, if facilities and boundaries arrive.
  - [ ] Institutional delivery reconciliation, if NFHS/HMIS district data is ready.

- [ ] Prepare a 3-minute script.
  - [ ] User question.
  - [ ] Trust Verdict.
  - [ ] Evidence and uncertainty.
  - [ ] Ranked fix.
  - [ ] Before/after proof.

- [ ] Verify quota safety.
  - [ ] App reads only.
  - [ ] No training live.
  - [ ] No writes live.
  - [ ] SQL Warehouse started before demo.

## Done Criteria

- [ ] All local tests pass.
- [ ] Bundle validates.
- [ ] Demo app opens.
- [ ] At least one end-to-end cached verdict works.
- [ ] Uncertainty is visible in the UI.
- [ ] README and runbook match the actual demo path.
