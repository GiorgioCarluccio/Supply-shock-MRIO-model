# Codex / Claude Code Prompt — Build Shock Calibration and Static Scenario Pipeline

You are working on the GitHub repository:

```text
Supply-shock-MRIO-model
```

The project currently has:

- validated heatwave exposure data;
- raw ISPRA flood and landslide exposure data;
- SAM data materialised locally;
- a working modelling layer based on the previous IO climate propagation model;
- a Python 3.12 `.venv` environment;
- no frontend yet.

The next goal is to build the **shock calibration and static scenario pipeline** for the MVP.

This pipeline should transform hazard exposure data into model-ready supply and demand shock vectors, run a fixed library of precomputed scenarios, and export dashboard-ready result tables.

Do **not** build the web app yet.

Do **not** introduce FastAPI, Next.js, Docker, Redis, Celery, databases, or cloud infrastructure.

Keep the implementation simple, explicit, local, and testable.

---

## 1. Project context

The project estimates the impact of climate-related physical risk shocks on Italian economic sectors at provincial level.

The model estimates **business interruption**, not physical asset damage.

The model operates on productive SAM nodes:

```text
province/region × sector
```

The model requires two shock vectors:

```text
sp = supply shock vector
sd = demand shock vector
```

Each vector must have length equal to the number of productive model nodes.

Model interpretation:

```text
X_cap = X0 * (1 - sp)
FD_post = FD0 * (1 - sd)
```

where:

```text
sp = reduction in productive capacity
sd = reduction in final demand
```

---

## 2. Existing heatwave data

The heatwave dataset already exists:

```text
data/processed/climate/province_heatwave_indicators.csv
```

Key fields:

```text
province_code
province_name
province_abbr
heatwave_exposure_raw
heatwave_exposure_weight
heatwave_exposure_method
```

Interpretation:

```text
heatwave_exposure_raw
= average annual provincial p75 hot days over 2011–2025,
  where hot day means TX >= 35°C
```

Construction logic:

1. Compute annual hot days per E-OBS grid cell.
2. For each province-year, take the p75 across grid cells.
3. For each province, average annual p75 values over 2011–2025.
4. Normalize against national mean.
5. Apply attenuation:

```text
heatwave_exposure_weight = clip(1 + 0.5 * (relative_exposure - 1), 0.10, 3.00)
```

Use `heatwave_exposure_weight` as the official provincial heatwave exposure multiplier.

Do not modify the heatwave methodology.

---

## 3. Uploaded ISPRA file for flood and landslide

The file is:

```text
province_pir.xlsx
```

It should be stored in the repository under:

```text
data/raw/ispra/province_pir.xlsx
```

Workbook structure observed:

```text
Sheet: data
Rows: 107 provinces
Columns of interest:
cod_reg
cod_prov
provincia
imidp3_p
imidp2_p
imidp1_p
imfrp4_p
imfrp3_p
imfrp2_p
imfrp1_p
```

Metadata sheet:

```text
Sheet: Metadati_PIR
```

Important indicators:

```text
imidp3_p = local business units at risk in high hydraulic hazard areas
imidp2_p = local business units at risk in medium hydraulic hazard areas
imidp1_p = local business units at risk in low hydraulic hazard areas

imfrp4_p = local business units at risk in very high landslide hazard areas P4
imfrp3_p = local business units at risk in high landslide hazard areas P3
imfrp2_p = local business units at risk in medium landslide hazard areas P2
imfrp1_p = local business units at risk in moderate landslide hazard areas P1
```

Observed values are stored as fractions between 0 and 1, despite metadata labels mentioning percentages.

Therefore the parser must validate units:

```text
if max(value) <= 1.5:
    treat as share in [0,1]
else:
    treat as percentage and divide by 100
```

Do not blindly divide by 100.

Approximate observed ranges from the uploaded workbook:

```text
flood high   imidp3_p: min 0, max about 0.246, mean about 0.053
flood medium imidp2_p: min about 0.001, max about 1.000, mean about 0.144
flood low    imidp1_p: min about 0.001, max about 1.000, mean about 0.268

landslide P4 imfrp4_p: min 0, max about 0.047, mean about 0.007
landslide P3 imfrp3_p: min 0, max about 0.093, mean about 0.012
landslide P2 imfrp2_p: min 0, max about 0.551, mean about 0.035
landslide P1 imfrp1_p: min 0, max about 0.518, mean about 0.039
```

---

## 4. Core calibration principle

Hazard exposure is not directly equal to output loss.

Convert exposure into **equivalent operational interruption days**, then into supply and demand shocks.

General formula:

```text
equivalent_stop_days[p, s, h, severity]
=
hazard_exposure_component[p, h, severity]
× base_interruption_days[h, severity]
× sector_vulnerability[s, h]
× scenario_intensity_multiplier
```

Then:

```text
supply_shock[p, s, h, severity]
=
equivalent_stop_days[p, s, h, severity] / working_days
```

with:

```text
working_days = 250
```

Demand shock:

```text
demand_shock[p, s, h, severity]
=
demand_pass_through_lambda[h] × supply_shock[p, s, h, severity]
```

Apply configurable caps:

```text
supply_shock = min(supply_shock, max_supply_shock)
demand_shock = min(demand_shock, max_demand_shock)
```

Default caps should be conservative and editable.

Suggested defaults:

```text
max_supply_shock = 0.25
max_demand_shock = 0.10
```

---

## 5. Hazard-specific calibration

### Heatwave

Use:

```text
heatwave_exposure_weight[p]
```

from `province_heatwave_indicators.csv`.

Default formula:

```text
equivalent_stop_days[p, s, heatwave, central]
=
base_interruption_days[heatwave, central]
× heatwave_exposure_weight[p]
× sector_vulnerability[s, heatwave]
× scenario_intensity_multiplier
```

Use a default central value such as:

```text
base_interruption_days[heatwave, central] = 5
```

Do not interpret every hot day as a full day of business interruption unless explicitly configured.

If desired, allow an alternative mode:

```text
heatwave_raw_days_mode = True
```

where:

```text
equivalent_stop_days = heatwave_exposure_raw × heatwave_day_to_stop_day_factor × sector_vulnerability
```

Default:

```text
heatwave_day_to_stop_day_factor = 0.20
```

but keep the central MVP mode based on `base_interruption_days × exposure_weight`.

### Flood

Use ISPRA local-unit exposure shares.

Map columns:

```text
flood_high   -> imidp3_p
flood_medium -> imidp2_p
flood_low    -> imidp1_p
```

Formula:

```text
equivalent_stop_days[p, s, flood, severity]
=
impacted_business_share[p, flood, severity]
× base_interruption_days[flood, severity]
× sector_vulnerability[s, flood]
× scenario_intensity_multiplier
```

Suggested editable default base days:

```text
flood_low    = 3
flood_medium = 10
flood_high   = 20
```

### Landslide

Use ISPRA local-unit exposure shares.

Map columns:

```text
landslide_p4 -> imfrp4_p
landslide_p3 -> imfrp3_p
landslide_p2 -> imfrp2_p
landslide_p1 -> imfrp1_p
```

Formula:

```text
equivalent_stop_days[p, s, landslide, severity]
=
impacted_business_share[p, landslide, severity]
× base_interruption_days[landslide, severity]
× sector_vulnerability[s, landslide]
× scenario_intensity_multiplier
```

Suggested editable default base days:

```text
landslide_p1 = 2
landslide_p2 = 5
landslide_p3 = 10
landslide_p4 = 20
```

---

## 6. Province-code mapping requirement

Climate exposure files use ISTAT province codes:

```text
province_code = cod_prov
```

The SAM productive model nodes may use NUTS/province region codes such as:

```text
ITC11
ITC12
...
```

The shock pipeline must not assume these identifiers are the same.

Create or require a crosswalk:

```text
data/processed/mappings/province_code_crosswalk.csv
```

Required columns:

```text
province_code
province_name
province_abbr
region_code
```

where:

```text
province_code = ISTAT numeric province code
region_code   = region/province code used in productive SAM nodes
```

If the crosswalk is missing, fail clearly with an actionable error message.

If the current SAM region code is already equal to `province_code`, allow this through an explicit config flag, but do not assume it silently.

---

## 7. Sector vulnerability

Create an editable sector-hazard vulnerability table.

Output path:

```text
data/processed/shocks/sector_hazard_vulnerability.csv
```

Columns:

```text
sector_code
macrosector_code
hazard
sector_vulnerability
rationale
```

If no expert table exists yet, generate a default placeholder from productive node sector codes.

Use macrosector defaults, editable by the user.

Suggested placeholder values:

```text
hazard      macrosector A   macrosector I   macrosector S
heatwave    0.70            0.40            0.30
flood       0.70            0.80            0.50
landslide   0.50            0.45            0.35
```

Do not present these defaults as empirically estimated values. Mark them as expert-placeholder assumptions.

---

## 8. Scenario library

Create a static scenario library.

Output path:

```text
data/processed/shocks/scenario_library.csv
```

Columns:

```text
scenario_id
hazard
severity
scenario_intensity
scenario_intensity_multiplier
base_interruption_days
demand_pass_through_lambda
max_supply_shock
max_demand_shock
is_dashboard_scenario
```

Suggested scenarios:

```text
heatwave_central

flood_low
flood_medium
flood_high

landslide_p1
landslide_p2
landslide_p3
landslide_p4
```

Optionally include internal calibration variants:

```text
conservative
central
stress
```

but for the static dashboard mark only the central/default scenario set as `is_dashboard_scenario = True`.

Suggested lambda values, editable:

```text
heatwave  = 0.10
flood     = 0.25
landslide = 0.15
```

---

## 9. Canonical hazard exposure table

Create:

```text
data/processed/climate/province_hazard_exposure.csv
```

Columns:

```text
province_code
province_name
province_abbr
hazard
severity
raw_exposure
exposure_weight
exposure_type
source_file
source_column
method
```

For heatwave:

```text
hazard = heatwave
severity = central
raw_exposure = heatwave_exposure_raw
exposure_weight = heatwave_exposure_weight
exposure_type = heatwave_hot_days_p75_annual_average
source_column = heatwave_exposure_raw / heatwave_exposure_weight
```

For flood and landslide:

```text
raw_exposure = impacted_business_share
exposure_weight = optional attenuated relative exposure
exposure_type = impacted_business_share
source_column = imidp*/imfrp*
```

For flood and landslide, compute an exposure weight for visualization:

```text
relative_exposure = raw_exposure / national_mean_raw_exposure
exposure_weight = clip(1 + attenuation * (relative_exposure - 1), 0.10, 3.00)
```

Default:

```text
attenuation = 0.50
```

However, the actual shock formula for flood and landslide should primarily use `raw_exposure` as impacted business share, not only the normalized exposure weight.

---

## 10. Shock matrix

Create:

```text
data/processed/shocks/shock_matrix.csv
```

Columns:

```text
scenario_id
hazard
severity
province_code
region_code
province_name
province_abbr
sector_code
macrosector_code
node_id
raw_exposure
exposure_weight
sector_vulnerability
base_interruption_days
scenario_intensity_multiplier
equivalent_stop_days
working_days
supply_shock
demand_pass_through_lambda
demand_shock
max_supply_shock
max_demand_shock
shock_method
```

This table should contain one row per:

```text
scenario × productive node
```

The script must validate that each productive model node receives a shock value.

If a node does not map to a province or sector, fail clearly.

---

## 11. Batch simulation runner

Create a script to run all dashboard scenarios using the calibrated shocks.

Input:

```text
data/processed/shocks/shock_matrix.csv
data/processed/model_inputs/
```

Output folder:

```text
data/processed/simulations/
```

For each `scenario_id`, save:

```text
data/processed/simulations/{scenario_id}/scenario_summary.json
data/processed/simulations/{scenario_id}/node_results.csv
data/processed/simulations/{scenario_id}/province_results.csv
data/processed/simulations/{scenario_id}/sector_results.csv
data/processed/simulations/{scenario_id}/top_penalized_flows.csv
data/processed/simulations/{scenario_id}/top_favored_flows.csv
data/processed/simulations/{scenario_id}/province_flow_heatmap.csv
data/processed/simulations/{scenario_id}/sector_flow_heatmap.csv
```

Do not require the frontend.

The simulation runner should be able to run one scenario at a time or all dashboard scenarios.

If the full model run is too heavy, allow a `--limit-scenarios` or explicit scenario selection argument.

---

## 12. Static dashboard export

Create consolidated dashboard files:

```text
data/processed/dashboard/scenario_index.json
data/processed/dashboard/kpi_summary.csv
data/processed/dashboard/province_losses.csv
data/processed/dashboard/sector_losses.csv
data/processed/dashboard/province_sector_losses.csv
data/processed/dashboard/top_penalized_flows.csv
data/processed/dashboard/top_favored_flows.csv
data/processed/dashboard/province_flow_heatmap.csv
data/processed/dashboard/sector_flow_heatmap.csv
```

These files should be frontend-ready.

They should not require live model execution.

---

## 13. Package structure

Create or update:

```text
src/climate_risk_io/shocks/
  __init__.py
  exposure_loader.py
  pir_parser.py
  sector_vulnerability.py
  scenario_library.py
  calibration.py
  shock_matrix.py
  batch_runner.py
  dashboard_exports.py
```

Keep code simple and explicit.

---

## 14. Scripts

Create:

```text
scripts/prepare_pir_exposure.py
scripts/build_hazard_exposure_table.py
scripts/build_sector_vulnerability_table.py
scripts/build_scenario_library.py
scripts/build_shock_matrix.py
scripts/run_static_scenarios.py
scripts/build_dashboard_outputs.py
scripts/test_shock_pipeline.py
```

### prepare_pir_exposure.py

Reads:

```text
data/raw/ispra/province_pir.xlsx
```

Writes a cleaned ISPRA exposure table:

```text
data/processed/climate/province_pir_clean.csv
```

Validation:

- 107 provinces expected;
- no missing `cod_prov`;
- no missing province names;
- all hazard columns numeric;
- exposure values converted to shares in `[0,1]`.

### build_hazard_exposure_table.py

Combines:

```text
province_heatwave_indicators.csv
province_pir_clean.csv
```

into:

```text
province_hazard_exposure.csv
```

### build_sector_vulnerability_table.py

Builds default editable sector vulnerability table from model productive nodes.

### build_scenario_library.py

Builds editable static scenario library.

### build_shock_matrix.py

Builds node-level shock matrix from:

```text
province_hazard_exposure.csv
sector_hazard_vulnerability.csv
scenario_library.csv
productive_nodes.csv
province_code_crosswalk.csv
```

### run_static_scenarios.py

Runs model for selected or all dashboard scenarios.

### build_dashboard_outputs.py

Aggregates simulation results into dashboard-ready static files.

### test_shock_pipeline.py

Runs non-Databricks tests.

It should validate:

- PIR Excel parser;
- heatwave exposure table availability;
- canonical exposure table;
- scenario library;
- sector vulnerability table;
- shock matrix dimensions;
- shock bounds;
- every productive node receives one shock per scenario;
- no null shock values;
- demand shock <= max demand shock;
- supply shock <= max supply shock.

---

## 15. README and docs

Create or update:

```text
docs/methodology/shock_calibration.md
```

Document:

- heatwave calibration;
- flood calibration;
- landslide calibration;
- equivalent stop days;
- supply shock formula;
- demand shock formula;
- sector vulnerability;
- scenario library;
- limitations.

Update README with:

```text
Shock calibration pipeline
```

Include commands:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_pir_exposure.py
.\.venv\Scripts\python.exe scripts\build_hazard_exposure_table.py
.\.venv\Scripts\python.exe scripts\build_sector_vulnerability_table.py
.\.venv\Scripts\python.exe scripts\build_scenario_library.py
.\.venv\Scripts\python.exe scripts\build_shock_matrix.py
.\.venv\Scripts\python.exe scripts\run_static_scenarios.py
.\.venv\Scripts\python.exe scripts\build_dashboard_outputs.py
.\.venv\Scripts\python.exe scripts\test_shock_pipeline.py
```

---

## 16. Important constraints

- Do not change the existing heatwave methodology.
- Do not change SAM ingestion unless required to load model inputs.
- Do not change the core model logic unless necessary to pass explicit shock vectors.
- Do not require Databricks for shock-pipeline tests.
- Do not build the web app yet.
- Do not hardcode secrets.
- Do not delete data.
- Do not over-engineer.

---

## 17. Final response required

After implementation, summarize:

- files created;
- files modified;
- PIR Excel parser implemented;
- hazard exposure table implemented;
- sector vulnerability table implemented;
- scenario library implemented;
- shock matrix implemented;
- static simulation runner implemented;
- dashboard export implemented;
- tests implemented;
- docs updated;
- commands to run;
- assumptions and limitations.

Explicitly report these assumptions:

1. ISPRA flood and landslide values are treated as shares if max <= 1.5.
2. Flood and landslide raw exposure represents share of local business units at risk.
3. Heatwave uses the validated `heatwave_exposure_weight`.
4. Equivalent stop days are scenario assumptions, not observed losses.
5. Sector vulnerability defaults are placeholders and must remain editable.
6. Demand shocks are derived as a hazard-specific fraction of supply shocks.
7. Generated dashboard files are static and do not require live model execution.
