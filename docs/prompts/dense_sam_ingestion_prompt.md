# Codex Prompt — Dense SAM Matrix Ingestion Without Full Parquet Storage

You are working on the GitHub repository `Supply-shock-MRIO-model`.

The project now uses one Python environment only:

```text
.venv
```

The environment is based on Python 3.12 and supports both:

- climate/geospatial processing;
- Databricks Connect / Databricks access.

Do not create or reference `.venv-databricks`.

## Project context

This repository is an MVP analytical engine for estimating the impact of climate-related physical risk shocks on Italian economic sectors at provincial level.

The final model will estimate business interruption effects, not physical asset damage. The main output will be lost value of production, in absolute and percentage terms, by province and sector.

The model will use a provincial Italian Social Accounting Matrix / Input-Output style matrix, with economic flows across:

```text
province × sector
```

The propagation model will later apply climate shocks to economic nodes and propagate impacts through the SAM network.

## Current issue

The previous SAM ingestion design attempted to store the full long-format SAM table locally as Parquet.

This is not viable because of size and memory constraints.

Also, a sparse strategy is not appropriate because the SAM has no truly zero entries in practice, and even very small entries are meaningful for the propagation model.

Therefore:

- do not sparsify;
- do not threshold;
- do not discard small values;
- do not require storing the full long SAM as Parquet.

The new design must materialize the SAM directly into a dense NumPy matrix artifact.

## Databricks SAM source

The Databricks table is:

```text
ml.sam.mrsam_downscaled_y
```

The table is in long format.

Available schema:

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

## Columns to use

For matrix construction, use only these columns:

```text
matrix_id
region_orig
ind_ava
region_dest
ind_use
value
time_period
row_label
col_label
```

Do not extract or store these columns in the model-ready artifacts:

```text
share
materialized_at
mlflow_experiment_name
mlflow_run_id
```

Exception: `materialized_at` may be queried only inside Databricks if needed to identify the latest materialization, but it should not be included in the final local matrix artifacts unless explicitly required for reporting.

## Column interpretation

```text
region_orig = supplier/origin region
ind_ava     = supplier/origin sector
region_dest = buyer/destination region
ind_use     = buyer/destination sector
value       = economic flow value
time_period = reference period
matrix_id   = matrix version identifier
row_label   = optional supplier node label
col_label   = optional buyer node label
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

Rows are supplier/origin nodes. Columns are buyer/destination nodes.

## Required output files

The core runtime artifacts should be:

```text
data/processed/sam/nodes.csv
data/processed/sam/z_matrix.npy
data/processed/sam/x_vector.npy
data/processed/sam/sam_build_report.json
```

Optional, if useful:

```text
data/processed/sam/province_mapping.csv
data/processed/sam/sector_mapping.csv
```

Do not make `data/interim/sam/sam_flows.parquet` a required artifact.

If any long-format local extract is retained, it must be explicitly marked as optional and not used by the runtime model.

## Repository changes required

Create or update these scripts:

```text
scripts/inspect_sam_databricks.py
scripts/build_sam_dense_matrix_from_databricks.py
scripts/test_sam_dense_matrix.py
```

Create or update these package files:

```text
src/climate_risk_io/sam/__init__.py
src/climate_risk_io/sam/databricks_client.py
src/climate_risk_io/sam/mappings.py
src/climate_risk_io/sam/loaders.py
src/climate_risk_io/sam/validators.py
src/climate_risk_io/sam/dense_builder.py
```

If older files exist for sparse or Parquet-first workflows, either:

- deprecate them clearly in comments and README; or
- update them to call the dense workflow; or
- remove references to them from README and tests.

Do not delete files unless clearly safe.

## Update config/paths.py

Ensure `config/paths.py` defines:

```python
SAM_PROCESSED_DIR = PROCESSED_DATA_DIR / "sam"
```

If `SAM_INTERIM_DIR` already exists, it may remain, but the dense matrix workflow should not depend on a full Parquet extract.

## mappings.py

Create or update `src/climate_risk_io/sam/mappings.py` with:

```python
SAM_TABLE = "ml.sam.mrsam_downscaled_y"

SAM_COLUMN_CONFIG = {
    "matrix_id": "matrix_id",
    "origin_region": "region_orig",
    "origin_sector": "ind_ava",
    "destination_region": "region_dest",
    "destination_sector": "ind_use",
    "flow_value": "value",
    "time_period": "time_period",
    "row_label": "row_label",
    "col_label": "col_label",
}

STANDARD_COLUMNS = {
    "matrix_id": "matrix_id",
    "origin_region": "origin_region",
    "origin_sector": "origin_sector",
    "destination_region": "destination_region",
    "destination_sector": "destination_sector",
    "flow_value": "flow_value",
    "time_period": "time_period",
    "row_label": "row_label",
    "col_label": "col_label",
}
```

Do not include `share`, `materialized_at`, `mlflow_experiment_name`, or `mlflow_run_id` as standard extraction columns.

## Script 1: inspect_sam_databricks.py

This script should inspect the Databricks table without downloading the full dataset.

It should print:

- table path;
- schema;
- sample rows;
- row count;
- available `matrix_id` values and row counts;
- available `time_period` values and row counts;
- number of unique origin regions;
- number of unique destination regions;
- number of unique origin sectors;
- number of unique destination sectors;
- total flow value;
- min/max flow value;
- number of null `value` rows;
- number of zero `value` rows;
- number of negative `value` rows;
- number of null origin/destination codes.

It may inspect `materialized_at` only to report available materializations or latest materialization, but this field should not be part of the final extracted matrix payload.

The script must not collect the full table locally.

## Script 2: build_sam_dense_matrix_from_databricks.py

Create or update:

```text
scripts/build_sam_dense_matrix_from_databricks.py
```

This script should connect to Databricks and build the dense local NumPy matrix.

At the top of the script, expose filters:

```python
FILTER_MATRIX_ID = None
FILTER_TIME_PERIOD = None
FILTER_LATEST_MATERIALIZATION = True
```

Behavior:

- If `FILTER_MATRIX_ID` is set, filter to that `matrix_id`.
- If `FILTER_TIME_PERIOD` is set, filter to that `time_period`.
- If `FILTER_LATEST_MATERIALIZATION = True`, use `materialized_at` only inside Databricks to filter to the latest available materialization after other filters.
- Do not include `materialized_at` in the local matrix artifact.

The script should select only:

```text
matrix_id
region_orig
ind_ava
region_dest
ind_use
value
time_period
row_label
col_label
```

Then standardize these names internally to:

```text
matrix_id
origin_region
origin_sector
destination_region
destination_sector
flow_value
time_period
row_label
col_label
```

### Databricks-side aggregation

Before local matrix construction, aggregate duplicate origin-destination-sector pairs in Databricks:

```text
origin_region
origin_sector
destination_region
destination_sector
```

using:

```text
SUM(flow_value)
```

Do not threshold values.

Do not discard small values.

### Node construction

Create the node universe as the union of:

```text
(origin_region, origin_sector)
(destination_region, destination_sector)
```

Create deterministic node IDs sorted by:

```text
region_code ascending, sector_code ascending
```

Save:

```text
data/processed/sam/nodes.csv
```

with columns:

```text
node_id
region_code
sector_code
node_label
```

where:

```text
node_label = "{region_code}__{sector_code}"
```

### Dense matrix construction

Build the matrix as a dense NumPy `.npy` file using memory mapping:

```python
np.lib.format.open_memmap
```

Output:

```text
data/processed/sam/z_matrix.npy
```

Use:

```text
dtype = float64
shape = (n_nodes, n_nodes)
```

Matrix orientation:

```text
row index    = supplier/origin node_id
column index = buyer/destination node_id
value        = flow_value
```

The script should fill the memory-mapped matrix from Databricks/Spark results.

If the full aggregated edge list is too large to collect safely, process it in manageable chunks or partitions.

Do not write a full long-format Parquet file as a required intermediate.

### Output vector

Compute:

```text
x[i] = sum_j Z[i, j]
```

Save:

```text
data/processed/sam/x_vector.npy
```

The vector must align with `nodes.csv` by `node_id`.

### Optional mappings

If useful, save:

```text
data/processed/sam/province_mapping.csv
data/processed/sam/sector_mapping.csv
```

with available region and sector codes.

### Build report

Create:

```text
data/processed/sam/sam_build_report.json
```

Include:

```text
table_name
filters_applied
columns_used
columns_excluded
n_nodes
matrix_shape
dtype
total_flow_value
min_flow_value
max_flow_value
negative_flow_count
zero_flow_count
null_flow_count
matrix_id_values
time_period_values
outputs_written
orientation
```

The `columns_excluded` field should include:

```text
share
materialized_at
mlflow_experiment_name
mlflow_run_id
```

The orientation field must state:

```text
rows = supplier/origin nodes; columns = buyer/destination nodes
```

## Runtime loader

Update:

```text
src/climate_risk_io/sam/loaders.py
```

Implement:

```python
def load_sam_dense_model(sam_dir: Path | None = None, mmap: bool = True) -> dict:
    ...
```

It should return:

```python
{
    "nodes": nodes_df,
    "Z": Z,
    "x": x,
    "report": report_dict,
}
```

If `mmap=True`, load the matrix with:

```python
np.load(path, mmap_mode="r")
```

If `mmap=False`, load normally.

The runtime loader must not connect to Databricks.

## Dense builder module

Create or update:

```text
src/climate_risk_io/sam/dense_builder.py
```

Implement reusable helpers for:

```python
build_nodes(...)
create_dense_memmap(...)
write_flows_to_dense_matrix(...)
compute_output_vector(...)
write_build_report(...)
```

Keep the implementation simple and readable.

## Validators

Update:

```text
src/climate_risk_io/sam/validators.py
```

Include validation helpers for:

```python
validate_required_columns(df, required_columns)
validate_no_nulls(df, columns)
validate_non_empty(df, name)
validate_dense_model_outputs(nodes, Z, x)
```

## Test script

Create or update:

```text
scripts/test_sam_dense_matrix.py
```

It should validate:

- `nodes.csv` exists;
- `z_matrix.npy` exists;
- `x_vector.npy` exists;
- `sam_build_report.json` exists;
- `Z` is square;
- `Z` dimension equals number of nodes;
- `x` length equals number of nodes;
- `sum(x)` equals `sum(Z)` within tolerance;
- no null node IDs;
- node IDs are unique;
- report orientation is correct;
- report `columns_excluded` includes `share`, `materialized_at`, `mlflow_experiment_name`, `mlflow_run_id`.

Print a clear pass/fail summary.

## README update

Update the SAM ingestion section.

Explain that:

- the SAM source is `ml.sam.mrsam_downscaled_y`;
- the full long SAM is not stored locally as Parquet;
- the core runtime artifact is `z_matrix.npy`;
- small flows are preserved;
- no sparsification is applied;
- selected columns are used only;
- excluded columns are `share`, `materialized_at`, `mlflow_experiment_name`, and `mlflow_run_id`;
- `materialized_at` may be used only for Databricks-side filtering to latest materialization;
- the matrix is loaded with NumPy and can be memory-mapped.

Document commands:

```powershell
.\.venv\Scripts\python.exe scripts\inspect_sam_databricks.py

.\.venv\Scripts\python.exe scripts\build_sam_dense_matrix_from_databricks.py

.\.venv\Scripts\python.exe scripts\test_sam_dense_matrix.py
```

## .gitignore update

Ensure generated artifacts are ignored:

```gitignore
data/processed/sam/
*.npy
data/**/*.json
```

Do not ignore source code, scripts, README, requirements, or config files.

## Constraints

Do not change heatwave scripts.

Do not delete data.

Do not hardcode secrets.

Do not use the 5 GB CSV as runtime input.

Do not introduce frontend, FastAPI, Docker, Redis, Celery, databases, or cloud deployment.

Keep implementation simple and explicit.

## Final response

After implementing, summarize:

- files created;
- files modified;
- old Parquet workflow removed or deprecated;
- dense matrix workflow added;
- columns used;
- columns excluded;
- how to run the SAM build;
- how to test the dense matrix;
- how to load the matrix at runtime;
- remaining manual configuration needed.
