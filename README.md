# Supply-shock-MRIO-model

This repository develops data-preparation and modeling tools for applying negative supply shocks to a multi-regional input-output / social accounting framework. The current work focuses on climate exposure inputs, starting with provincial heatwave exposure indicators for Italy.

## Current Purpose

The repository is currently an early-stage data-preparation workspace. It prepares E-OBS climate data and ISTAT province geometries, computes provincial heatwave exposure indicators, and produces diagnostic outputs for later integration into the MRIO shock model.

It is not yet a web application and does not use databases, APIs, Docker, or frontend code.

## Heatwave Exposure Indicator

The current heatwave exposure indicator uses E-OBS daily maximum temperature (`tx`) over Italy. The workflow:

1. extracts the Italy bounding box for 1991-2025;
2. spatially joins E-OBS grid-cell centroids to ISTAT provinces;
3. computes annual hot days per grid cell where `TX >= 35 deg C`;
4. aggregates grid cells to province-year indicators using mean, median, p75, p90, and max;
5. uses the p75 statistic across grid cells as the official raw exposure metric;
6. averages annual p75 values over 2011-2025;
7. normalizes against the national mean;
8. applies attenuation with `1 + 0.5 * (relative_exposure - 1)`;
9. clips the attenuated weight between `0.10` and `3.00`.

The official heatwave exposure field is `heatwave_exposure_weight`.

## Folder Structure

```text
Supply-shock-MRIO-model/
  config/
    paths.py
  data/
    raw/
      eobs/
      istat/
      ispra/
    interim/
    processed/
      climate/
        maps/
  scripts/
    prepare_heatwave_inputs.py
    compute_heatwave_province_indicators.py
    plot_heatwave_cells_map.py
    test_heatwave_outputs.py
    inspect_sam_databricks.py
    build_sam_dense_matrix_from_databricks.py
    test_sam_dense_matrix.py
    extract_sam_from_databricks.py   (deprecated)
    build_sam_model_inputs.py        (deprecated)
    test_sam_outputs.py              (deprecated)
    build_model_inputs_from_sam.py
    run_model_smoke_test.py
    test_model_layer.py
    enrich_sam_nodes_with_macrosector.py
  src/
    climate_risk_io/
      climate/
      io_utils/
      sam/
      model/
  docs/
    methodology/
      model_layer.md
      sam_account_structure.md
    prompts/
```

Large raw and generated data files are intentionally excluded from Git. Keep local copies under `data/raw/`, `data/interim/`, and `data/processed/`.

## Python environment

The project uses one Python environment only: `.venv`.

The `.venv` environment must be based on Python 3.12. This single environment is used for climate processing, repository tests, geospatial processing, NetCDF handling, and Databricks Connect.

To recreate the environment, run:

```powershell
.\setup_env.ps1
```

To test the repository, run:

```powershell
.\run_project_test.ps1
```

VSCode should use:

```text
.venv\Scripts\python.exe
```

The scripts expect the following local inputs:

```text
data/raw/eobs/tg_ens_mean_0.1deg_reg_v33.0e.nc
data/raw/eobs/tx_ens_mean_0.1deg_reg_v33.0e.nc
data/raw/istat/ProvCM01012024_g/
data/raw/ispra/province_pir.xlsx
```

## Running The Workflow

Run commands from the project root:

```bash
python scripts/prepare_heatwave_inputs.py
python scripts/compute_heatwave_province_indicators.py
python scripts/plot_heatwave_cells_map.py
python scripts/test_heatwave_outputs.py
```

The main processed outputs are written under:

```text
data/processed/climate/
```

## SAM Ingestion Pipeline (Dense Matrix)

The SAM ingestion pipeline reads the Databricks source table
`ml.sam.mrsam_downscaled_y` and materializes a **dense** flow matrix directly to
local disk as a memory-mapped NumPy array. The full long-format SAM is **not**
stored locally as Parquet.

Key design points:

* the SAM has no truly zero entries in practice, and even very small values are
  meaningful for the propagation model, so **no sparsification or thresholding**
  is applied;
* the core runtime artifact is `data/processed/sam/z_matrix.npy`, a dense
  `float64` matrix loaded with NumPy (and memory-mappable);
* only the columns needed to build the matrix are used:
  `matrix_id`, `region_orig`, `ind_ava`, `region_dest`, `ind_use`, `value`,
  `time_period`, `row_label`, `col_label`;
* the columns `share`, `materialized_at`, `mlflow_experiment_name` and
  `mlflow_run_id` are **excluded** from the local artifacts;
* `materialized_at` is queried **only inside Databricks** to filter to the
  latest materialization — it is never written to the matrix artifacts.

The source table is in long format with supplier fields `region_orig` and
`ind_ava`, buyer fields `region_dest` and `ind_use`, and flow value `value`.

Matrix convention:

```text
Z[i, j] = flow from supplier node i to buyer node j
rows    = supplier/origin nodes
columns = buyer/destination nodes
```

where:

```text
i = (region_orig, ind_ava)
j = (region_dest, ind_use)
Z[i, j] = value
```

### Databricks authentication

The SAM scripts authenticate via Databricks Connect. When the Databricks VS Code
extension is running, it publishes auth settings (host, serverless compute, and a
local metadata-service token endpoint) to `.databricks/.databricks.env`. The
client (`src/climate_risk_io/sam/databricks_client.py`) loads the project `.env`
and then that file automatically, so **running the scripts from a plain terminal
reuses the same authentication as the notebooks** — provided VS Code and the
extension are running.

For headless / CI runs (extension not running), configure credentials instead,
e.g. `databricks auth login --host <workspace-url>` or a PAT in `.env`.

Run commands from the project root using the single `.venv` environment.

Inspect the Databricks table without downloading the full dataset:

```powershell
.\.venv\Scripts\python.exe scripts\inspect_sam_databricks.py
```

Build the dense matrix (aggregates on the cluster, fills a memory-mapped matrix
in chunks by origin region):

```powershell
.\.venv\Scripts\python.exe scripts\build_sam_dense_matrix_from_databricks.py
```

Before building, set these optional filters near the top of
`scripts/build_sam_dense_matrix_from_databricks.py` if needed:

```python
FILTER_MATRIX_ID = None
FILTER_TIME_PERIOD = None
FILTER_LATEST_MATERIALIZATION = True
```

Test the generated dense matrix:

```powershell
.\.venv\Scripts\python.exe scripts\test_sam_dense_matrix.py
```

Load the matrix at runtime (no Databricks connection required):

```python
from climate_risk_io.sam.loaders import load_sam_dense_model

model = load_sam_dense_model(mmap=True)  # mmap keeps the matrix off-RAM
nodes, Z, x, report = model["nodes"], model["Z"], model["x"], model["report"]
```

Generated files are written under `data/processed/sam/` and are excluded from
Git:

```text
data/processed/sam/nodes.csv
data/processed/sam/z_matrix.npy
data/processed/sam/x_vector.npy
data/processed/sam/sam_build_report.json
data/processed/sam/province_mapping.csv   (optional)
data/processed/sam/sector_mapping.csv     (optional)
```

The earlier Parquet-first / sparse scripts
(`extract_sam_from_databricks.py`, `build_sam_model_inputs.py`,
`test_sam_outputs.py`) are **deprecated** and now print a pointer to the dense
workflow.

The dense `nodes.csv` now also carries a `macrosector_code` column and a
canonical three-part `region__sector__macrosector` `node_label`. The macrosector
is the third `__`-separated part of the source `row_label` / `col_label` and is
required by the modelling layer to split accounts into productive, final-demand
and value-added blocks. New builds emit it automatically; an artifact built
before this change can be upgraded locally with:

```powershell
.\.venv\Scripts\python.exe scripts\enrich_sam_nodes_with_macrosector.py
```

## Modelling Layer

The modelling layer (`src/climate_risk_io/model/`) turns the dense SAM into a
region-sector input-output propagation model that estimates **business
interruption** (lost value of production) from physical-risk supply shocks.

### SAM account classification

Every account is parsed from its canonical label
`region_code__sector_code__macrosector_code` and classified by macrosector:

```text
productive    = {A, I, S}          (agriculture, industry, services)
value added   = {L, K, T}          (labour, capital, indirect taxes)
final demand  = {HH, CF, G, R}     (households, capital formation, government, rest of world)
```

`ROW` (macrosector `R`) is treated as final demand. The propagation model runs
**only on the productive block**.

### Model input construction

`build_model_inputs_from_sam.py` slices the productive block out of the full SAM:

```text
Z0  = productive rows x productive columns
FD0 = productive rows x final-demand columns, summed per productive row
VA0 = value-added rows x productive columns
X0  = row_sum(Z0) + FD0
```

It also reports a row-vs-column output reconciliation gap (`X0` vs
`intermediate_inputs_by_column + value_added_by_column`). Row and column output
are **not** forced equal; a large gap is reported and warned about.

Outputs are written to `data/processed/model_inputs/` (`Z0.npy`, `FD0.npy`,
`X0.npy`, `VA0.npy`, `globsec_of.npy`, `productive_nodes.csv`,
`account_nodes.csv`, `sector_mapping.csv`, `model_input_report.json`).

### Propagation model

`IOClimateModel.run(sd, sp, gamma, substitution_p)` takes explicit demand
(`sd`) and supply (`sp`) shock vectors and iterates a demand-only outer loop:
supplier rationing, a **CES input bottleneck** (weighted by input cost shares,
tunable via `substitution_p`), within-sector-group inventory reallocation, a
capacity cap, and a monotone final-demand update until convergence. The
demand-only output requirement is obtained by solving `(I - A0) X = FD` with a
reusable LU factorisation rather than forming the dense Leontief inverse. The
CES bottleneck replaces the reference strict-min Leontief bottleneck, which
over-propagated trivial universal suppliers; the aggregated global-feasibility
cap is off by default (it does not converge in the outer loop). Indirect
propagation is currently modest pending a redesign — see
[docs/methodology/model_layer.md](docs/methodology/model_layer.md) §5.

### Commands

Build model inputs from the SAM:

```powershell
.\.venv\Scripts\python.exe scripts\build_model_inputs_from_sam.py
```

Run the propagation smoke test (subset by default; `--full` for the whole block):

```powershell
.\.venv\Scripts\python.exe scripts\run_model_smoke_test.py
```

Run the non-Databricks model-layer tests:

```powershell
.\.venv\Scripts\python.exe scripts\test_model_layer.py
```

Run the global project setup test:

```powershell
.\.venv\Scripts\python.exe test_project_setup.py
```

## Shock calibration pipeline

The shock calibration pipeline turns hazard exposure data (heatwave, flood,
landslide) into model-ready supply and demand shock vectors, runs a fixed
library of precomputed scenarios through the propagation model, and exports
static, dashboard-ready result tables. It is local, explicit and testable: no
FastAPI, Next.js, Docker, Redis, Celery, database or cloud dependency.

Hazard exposure is converted into *equivalent operational interruption days*,
then into shocks:

```text
equivalent_stop_days = exposure_component × base_interruption_days
                       × sector_vulnerability × scenario_intensity_multiplier
supply_shock = min(equivalent_stop_days / 250, max_supply_shock)   # default cap 0.25
demand_shock = min(lambda × supply_shock, max_demand_shock)        # default cap 0.10
```

Heatwave uses the validated `heatwave_exposure_weight`; flood and landslide use
the ISPRA share of local business units at risk. Climate files use ISTAT
province codes and the SAM nodes use NUTS-3 region codes, so the pipeline builds
and validates a `province_code_crosswalk.csv` and never assumes the two systems
are equal. See
[docs/methodology/shock_calibration.md](docs/methodology/shock_calibration.md)
for the full methodology and limitations.

The package lives in `src/climate_risk_io/shocks/` (`pir_parser`,
`exposure_loader`, `sector_vulnerability`, `scenario_library`, `calibration`,
`shock_matrix`, `batch_runner`, `dashboard_exports`).

### Commands

Run the steps in order from the project root:

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

`build_sector_vulnerability_table.py` and `build_scenario_library.py` keep an
existing (hand-edited) CSV in place unless run with `--force`. The full model
run is heavy; `run_static_scenarios.py` accepts `--scenarios <id ...>` and
`--limit-scenarios N` to run a subset.

### Outputs

```text
data/processed/mappings/province_code_crosswalk.csv
data/processed/climate/province_pir_clean.csv
data/processed/climate/province_hazard_exposure.csv
data/processed/shocks/sector_hazard_vulnerability.csv
data/processed/shocks/scenario_library.csv
data/processed/shocks/shock_matrix.csv
data/processed/simulations/<scenario_id>/...
data/processed/dashboard/...
```

> Note: the static simulation totals are produced by the committed strict-min
> reference propagation model, which has a known, deferred over-propagation /
> non-convergence issue on the full economy (see
> [docs/methodology/model_layer.md](docs/methodology/model_layer.md) §5). The
> shock-calibration layer is independent of and unaffected by that issue.
