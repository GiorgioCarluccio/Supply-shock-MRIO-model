# Data Regeneration Map

How to rebuild the entire `data/` tree and repopulate the static dashboard after a
local-data loss. All of `data/raw`, `data/interim`, and `data/processed` are
**git-ignored** (only `.gitkeep` placeholders are tracked), so **git cannot
restore them** — they must be recovered from backup (OneDrive recycle bin / another
synced machine) or regenerated from external source data with the pipeline below.

> Fastest recovery: restore `data/processed/` from OneDrive's online recycle bin,
> then only Stage H (frontend export) + the ISTAT shapefile (for the map) need to
> re-run. Full regeneration (below) is the fallback when no backup exists.

Run every command from the repo root using the single project environment:
`.venv\Scripts\python.exe`.

## External source data (the hard blockers)

All four are absent after the loss and must be re-acquired **before** anything runs.

| # | Source | Lands at | Notes |
|---|---|---|---|
| 1 | Databricks table `ml.sam.mrsam_downscaled_y` | read live (no local file) | Databricks Connect — VS Code Databricks extension running, or `databricks auth login` / PAT in `.env` |
| 2 | E-OBS `tx_ens_mean_0.1deg_reg_v33.0e.nc` | `data/raw/eobs/` | E-OBS / ECA&D portal (registration). README also lists `tg_...nc` but active scripts only read `tx_`. |
| 3 | ISTAT 2024 provinces shapefile `ProvCM01012024_g/` (`.shp/.shx/.dbf/.prj`) | `data/raw/istat/` | ISTAT "Confini delle unità amministrative a fini statistici 2024" |
| 4 | ISPRA `province_pir.xlsx` | `data/raw/ispra/` | ISPRA PIR (flood / landslide risk shares) |

## Pipeline (execution order)

```
STAGE A · Climate/heatwave            needs: E-OBS tx.nc + ISTAT .shp
  A1  prepare_heatwave_inputs.py
        -> climate/eobs_tx_italy_1991_2025.nc, climate/istat_provinces_2024.gpkg
  A2  compute_heatwave_province_indicators.py
        -> climate/province_heatwave_indicators.csv   (heatwave_exposure_weight)

STAGE B · PIR exposure                needs: ISPRA .xlsx
  B1  prepare_pir_exposure.py
        -> climate/province_pir_clean.csv

STAGE C · SAM (Databricks)            needs: Databricks auth
  C1  build_sam_dense_matrix_from_databricks.py
        -> sam/{nodes.csv, z_matrix.npy, x_vector.npy, sam_build_report.json}
  C3  build_model_inputs_from_sam.py
        -> model_inputs/{Z0,FD0,X0,VA0}.npy, productive_nodes.csv,
           account_nodes.csv, globsec_of.npy, sector_mapping.csv,
           model_input_report.json
  (C2 enrich_sam_nodes_with_macrosector.py  — only to upgrade an OLD sam build that
       lacks macrosector_code; new C1 builds emit it automatically)

STAGE D · Hazard table + crosswalk    needs: A2 + B1 + A1 gpkg
  D1  build_hazard_exposure_table.py
        -> climate/province_hazard_exposure.csv
        -> mappings/province_code_crosswalk.csv     (NUTS-3 <-> ISTAT join key)

STAGE E · Shock matrix                needs: D1 + C3 productive_nodes
  E1  build_sector_vulnerability_table.py   -> shocks/sector_hazard_vulnerability.csv
  E2  build_scenario_library.py             -> shocks/scenario_library.csv
        (E1/E2 write sensible defaults and keep an existing CSV unless --force;
         these were hand-editable — re-apply any manual tweaks here)
  E3  build_shock_matrix.py                 -> shocks/shock_matrix.csv

STAGE F · Run model (HEAVY)           needs: E3 + C3
  F1  run_static_scenarios.py
        -> simulations/<scenario_id>/...
        Scenarios: flood_low/medium/high, heatwave_central, landslide_p1..p4
        Subset flags: --scenarios <id ...>, --limit-scenarios N
        WARNING: known over-propagation / non-convergence on the full economy
                 (docs/methodology/model_layer.md §5). Stress-testing this is a
                 separate workstream.

STAGE G · Dashboard tables            needs: F1
  G1  build_dashboard_outputs.py
        -> dashboard/{scenario_index.json, kpi_summary.csv, province_losses.csv,
           sector_losses.csv, province_sector_losses.csv, top_penalized_flows.csv,
           top_favored_flows.csv, province_flow_heatmap.csv, sector_flow_heatmap.csv}

STAGE H · Frontend export             needs: G1 + D1 + climate + mappings
                                              + C3 sector_mapping + ISTAT .shp
  H1  export_province_geojson_for_frontend.py
        -> frontend/public/data/geographies/italy_provinces.geojson
  H2  export_dashboard_data_for_frontend.py
        -> frontend/public/data/*.json    (fixes the dashboard "no data" message)
  (H3 test_frontend_data_export.py — optional validation of the export + joins)
```

## Validation gates

Run after the relevant stage to confirm before proceeding:

- `test_sam_dense_matrix.py`     — after C1
- `test_model_layer.py`          — after C3
- `test_shock_pipeline.py`       — after E3 / the shock layer
- `test_frontend_data_export.py` — after H2

## Key facts / gotchas

- **No shortcut to the dashboard.** Stage H2 needs `dashboard/`, `shocks/`,
  `climate/province_hazard_exposure.csv`, `mappings/province_code_crosswalk.csv`,
  **and** `model_inputs/sector_mapping.csv` (a Databricks-derived file). The whole
  chain feeds it.
- **Databricks is the deepest dependency.** No SAM -> no model_inputs -> no
  shock_matrix -> no simulations -> no dashboard.
- **The crosswalk** (`province_code_crosswalk.csv`, built in D1) is the join key:
  climate files use ISTAT province codes, SAM nodes use NUTS-3 region codes.
- **Frontend runtime:** `node_modules` is also git-ignored and was lost in the same
  incident; `npm install` in `frontend/` regenerates it. The dashboard expects
  `max_iter = 1`, `gamma = 0.5`; stored outputs that differ surface an in-app caveat.
- **OneDrive caveat:** this repo lives under OneDrive. `node_modules` and `data/`
  were left as cloud-only/empty after a branch switch + sync. Prefer the OneDrive
  recycle bin for recovery; git is no help for ignored files.
