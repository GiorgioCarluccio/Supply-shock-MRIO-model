You are working on the GitHub repository `Supply-shock-MRIO-model`.

Before making further changes, inspect the repository and verify that the current structure is coherent.

This is an inspection and validation pass. Do not refactor aggressively. Do not delete data. Do not change scientific methodology. If you find issues, report them first and only apply small, safe fixes if they are clearly necessary to make tests/imports work.

## Overall project context

The project is an MVP analytical engine for estimating the impact of climate-related physical risk shocks on Italian economic sectors at provincial level.

The final application will estimate business interruption effects, not physical asset damage. The main output will be lost value of production, both in absolute terms and percentage terms, by geography and sector.

The model will use a provincial Italian Social Accounting Matrix / Input-Output style matrix, with economic flows across:

```text
province × sector
```

The propagation model will later apply climate shocks to economic nodes and propagate impacts through the SAM network.

The frontend/backend web application is not yet being built. The current repository is focused on:

1. climate exposure data preparation;
2. SAM ingestion and model-ready input preparation;
3. clean local Python project structure;
4. reproducible scripts and tests.

## Work completed so far

### 1. Repository organization

The repository has been reorganized into a cleaner structure:

```text
config/
data/
scripts/
src/climate_risk_io/
README.md
requirements.txt
test_project_setup.py
```

The repository uses one Python virtual environment only:

```text
.venv
```

This environment is based on Python 3.12 and is intended to support both:

* climate/geospatial processing;
* Databricks Connect / Databricks access.


### 2. Heatwave exposure module

The heatwave exposure component has been built and validated.

Source data:

* E-OBS `tx`, daily maximum temperature;
* ISTAT 2024 province shapefile.

Methodology:

* extract Italy bounding box from E-OBS;
* use period `1991-2025`;
* compute annual hot days per grid cell where `TX >= 35°C`;
* spatially assign E-OBS grid-cell centroids to ISTAT provinces;
* aggregate grid cells to province-year indicators using mean, median, p75, p90 and max;
* define official raw heatwave exposure as the average over `2011-2025` of the annual provincial p75 hot-day statistic;
* normalize against the national mean;
* apply attenuation:

```text
attenuated_weight = 1 + 0.5 * (relative_exposure - 1)
```

* clip the final weight between `0.10` and `3.00`;
* save the official field as:

```text
heatwave_exposure_weight
```

Current generated files include:

```text
data/processed/climate/eobs_tx_italy_1991_2025.nc
data/processed/climate/istat_provinces_2024.gpkg
data/processed/climate/province_heatwave_indicators.csv
data/processed/climate/province_heatwave_indicators_yearly.csv
data/processed/climate/maps/
```

The existing root test script should validate the heatwave outputs.

### 3. SAM ingestion module

A SAM ingestion layer has started.

The SAM source table is in Databricks:

```text
ml.sam.mrsam_downscaled_y
```

The table is in long format.

Schema:

```text
matrix_id                string
region_orig              string
ind_ava                  string
region_dest              string
ind_use                  string
value                    double
share                    double
time_period              int
materialized_at          timestamp
mlflow_experiment_name   string
mlflow_run_id            string
row_label                string
col_label                string
```

Model interpretation:

```text
region_orig = supplier/origin region
ind_ava     = supplier/origin sector
region_dest = buyer/destination region
ind_use     = buyer/destination sector
value       = economic flow value
```

The matrix convention must be:

```text
Z[i, j] = flow from supplier node i to buyer node j
```

where:

```text
i = (region_orig, ind_ava)
j = (region_dest, ind_use)
Z[i, j] = value
```

The SAM ingestion additions are expected to include:

```text
scripts/inspect_sam_databricks.py
scripts/extract_sam_from_databricks.py
scripts/build_sam_model_inputs.py
scripts/test_sam_outputs.py

src/climate_risk_io/sam/__init__.py
src/climate_risk_io/sam/databricks_client.py
src/climate_risk_io/sam/mappings.py
src/climate_risk_io/sam/loaders.py
src/climate_risk_io/sam/validators.py
src/climate_risk_io/sam/sparse_builder.py
```

Expected SAM local outputs after successful extraction/build:

```text
data/interim/sam/sam_flows.parquet

data/processed/sam/nodes.csv
data/processed/sam/province_mapping.csv
data/processed/sam/sector_mapping.csv
data/processed/sam/z_matrix_sparse.npz
data/processed/sam/x_vector.parquet
data/processed/sam/sam_build_report.json
```

## What you must do now

Perform a careful repository inspection.

### 1. Inspect repository structure

Check that the main structure is coherent:

```text
config/
data/
scripts/
src/climate_risk_io/
README.md
requirements.txt
test_project_setup.py
```

Check that the SAM-related files exist if they were added.

Check that no scripts still reference `.venv-databricks`.

Check that `.vscode/settings.json`, if present, points to:

```text
.venv\Scripts\python.exe
```

### 2. Inspect configuration

Open and inspect:

```text
config/paths.py
```

Verify that it defines at least:

```python
PROJECT_ROOT
DATA_DIR
RAW_DATA_DIR
INTERIM_DATA_DIR
PROCESSED_DATA_DIR
CLIMATE_PROCESSED_DIR
CLIMATE_MAPS_DIR
SAM_INTERIM_DIR
SAM_PROCESSED_DIR
```

If `SAM_INTERIM_DIR` or `SAM_PROCESSED_DIR` is missing, add them.

### 3. Inspect dependencies

Open:

```text
requirements.txt
```

Verify that it contains dependencies needed for:

* pandas;
* numpy;
* scipy;
* pyarrow;
* xarray;
* netcdf4;
* dask;
* geopandas;
* pyogrio;
* shapely;
* matplotlib;
* openpyxl;
* python-dotenv;
* databricks-connect;
* databricks-sql-connector.

Do not pin versions unless they are already pinned.

### 4. Run repository test

Run:

```powershell
.\.venv\Scripts\python.exe test_project_setup.py
```

Report whether it passes.

If it fails because of a missing package, report the missing package and suggest the minimal install command.

Do not alter the heatwave methodology.

### 5. Static-test the SAM additions

Because Databricks authentication is not configured yet, do not require a live Databricks connection for this pass.

Instead:

* compile all SAM Python files;
* import all SAM package modules;
* verify that scripts can be parsed;
* verify that the SAM mapping uses the correct table and columns.

Check these files:

```text
scripts/inspect_sam_databricks.py
scripts/extract_sam_from_databricks.py
scripts/build_sam_model_inputs.py
scripts/test_sam_outputs.py

src/climate_risk_io/sam/databricks_client.py
src/climate_risk_io/sam/mappings.py
src/climate_risk_io/sam/loaders.py
src/climate_risk_io/sam/validators.py
src/climate_risk_io/sam/sparse_builder.py
```

The mapping must reflect:

```python
SAM_TABLE = "ml.sam.mrsam_downscaled_y"

region_orig -> origin_region
ind_ava     -> origin_sector
region_dest -> destination_region
ind_use     -> destination_sector
value       -> flow_value
time_period -> time_period
matrix_id   -> matrix_id
row_label   -> row_label
col_label   -> col_label
share       -> share
```

### 6. Check SAM scripts conceptually

Verify that:

* `inspect_sam_databricks.py` does not download the full table;
* `extract_sam_from_databricks.py` writes to `data/interim/sam/sam_flows.parquet`;
* `build_sam_model_inputs.py` reads from `data/interim/sam/sam_flows.parquet`;
* `build_sam_model_inputs.py` writes model-ready outputs to `data/processed/sam/`;
* `test_sam_outputs.py` validates the processed SAM outputs;
* runtime loaders do not connect to Databricks;
* sparse matrix orientation is documented as:

```text
row = supplier/origin node
column = buyer/destination node
```

### 7. Add a SAM static test if missing

If no static SAM test exists, create a lightweight root script:

```text
test_sam_static_setup.py
```

It should check:

* expected SAM files exist;
* expected SAM package modules import;
* `SAM_TABLE` equals `ml.sam.mrsam_downscaled_y`;
* required mapping keys exist;
* scripts compile;
* `config.paths` contains SAM directories.

It should print a clear pass/fail summary.

### 8. Update README if needed

If README does not already document the SAM ingestion pipeline, add a concise section:

```text
SAM ingestion pipeline
```

Include:

* Databricks table path;
* schema interpretation;
* matrix convention;
* scripts and commands;
* note that generated Parquet, NPZ and JSON files are excluded from Git.


Return a concise inspection report with:

* repository status;
* tests run;
* tests passed/failed;
* SAM files found/missing;
* small fixes applied;
* remaining blockers;
* next recommended command.

The next recommended command should likely be:

```powershell
.\.venv\Scripts\python.exe test_sam_static_setup.py
```


