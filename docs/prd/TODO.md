# TODO

## Immediate Next Steps

- [x] Create or confirm the Unity Catalog structure.
  - [x] `data_readiness_desk`
  - [x] `data_readiness_desk.bronze`
  - [x] `data_readiness_desk.pipeline`
  - [x] `/Volumes/data_readiness_desk/bronze/files/`

- [ ] Upload or copy source files into the Volume.
  - [x] `hmis_2019_20_slice.csv`
  - [x] Facilities source table access granted
  - [ ] `india_post_pincode_directory.csv` when available
  - [x] `srs_2020_state.csv` generated locally and uploaded
  - [x] `india_districts.geojson` generated locally and uploaded

- [x] Run bundle pipeline in dev.
  - [x] `databricks bundle validate --target dev`
  - [x] `databricks bundle deploy --target dev`
  - [x] `databricks bundle run virtue_foundation_pipeline --target dev`

- [x] Validate currently implemented outputs.
  - [x] `bronze_hmis_2019_20_slice`
  - [x] `silver_hmis_2019_20_long`
  - [x] `silver_hmis_2019_20_indicator_totals`
  - [x] `gold_hmis_state_indicator_summary`
  - [x] `silver_facilities_geo` has 10,088 rows in dev.
  - [x] `gold_facility_verdicts` has 255 rows in dev.

- [x] Deploy Free Databricks App in dev.
  - [x] App name: `data-readiness-desk`
  - [x] Active deployment: `01f1693dbc0e1115aa0cc8b6b8422304`
  - [x] URL: `https://data-readiness-desk-7474647240221945.aws.databricksapps.com`

## Build Work

- [x] Add preflight validation task.
  - [x] Check source Volume exists.
  - [x] Check expected files exist.
  - [x] Check facilities table path is configured and readable.
  - [ ] Check NFHS table path is configured and readable.
  - [x] Fail with clear messages before Spark reads.

- [ ] Build facility location lens.
  - [x] Ingest facilities shared table into bronze.
  - [x] Generate `india_districts.geojson` locally.
  - [x] Upload `india_districts.geojson`.
  - [ ] Build point-in-polygon assignment.
  - [x] Publish first-pass `silver_facilities_geo`.
  - [x] Publish first-pass `gold_facility_verdicts`.

- [ ] Build disease lens.
  - [x] Publish state-grain HMIS fallback summary for demo.
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

- [ ] Wire Free Databricks App.
  - [x] Read real cached gold tables.
  - [x] Add verdict card.
  - [x] Wire verdict card to selected cached output.
  - [x] Add table view.
  - [x] Add map-style coordinate preview.
  - [x] Add ranked fixes.
  - [x] Add simulated before/after score lift.
  - [x] Enforce read-only, gold-only queries for current API.
  - [x] Confirm the app runs as a Free Databricks App, not externally hosted web app.

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

- [x] Verify quota safety.
  - [x] App reads only.
  - [x] No training live.
  - [x] No writes live.
  - [x] SQL Warehouse started before demo.

## Done Criteria

- [ ] All local tests pass.
- [ ] Bundle validates.
- [x] Demo app deploys.
- [x] At least one end-to-end cached verdict works.
- [x] Uncertainty is visible in the UI.
- [x] README and runbook match the actual demo path.
