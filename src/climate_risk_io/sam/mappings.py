"""Column mappings for the SAM Databricks source table.

The dense-matrix ingestion workflow uses only the columns needed to build the
node universe and the flow matrix. ``share`` and the MLflow / materialization
bookkeeping columns are intentionally excluded from the model-ready artifacts.
"""

SAM_TABLE = "ml.sam.mrsam_downscaled_y"

# Columns used to build the dense matrix. Source column name on the right.
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

# Standardized internal names after selection/aliasing.
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

# Source column queried ONLY inside Databricks to pick the latest
# materialization. It is never written to the local matrix artifacts.
MATERIALIZED_AT_COLUMN = "materialized_at"

# Columns deliberately excluded from the model-ready artifacts.
COLUMNS_EXCLUDED = [
    "share",
    "materialized_at",
    "mlflow_experiment_name",
    "mlflow_run_id",
]
