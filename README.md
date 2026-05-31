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
  src/
    climate_risk_io/
      climate/
      io_utils/
      sam/
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
