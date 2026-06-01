"""Build a dense local SAM matrix directly from Databricks.

This connects to Databricks, aggregates flows on the cluster, then materializes
a dense float64 matrix into a memory-mapped ``.npy`` file on local disk. The
full long-format SAM is never collected locally: flows are pulled and written
in chunks (one origin region at a time) to keep memory bounded.

Matrix convention:

    Z[i, j] = flow from supplier node i to buyer node j
    rows = supplier/origin nodes; columns = buyer/destination nodes

Run from the project root:

    .\\.venv\\Scripts\\python.exe scripts\\build_sam_dense_matrix_from_databricks.py
"""

import sys
from pathlib import Path

import numpy as np
from pyspark.sql import functions as F


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from climate_risk_io.sam.databricks_client import read_sam_table
from climate_risk_io.sam.dense_builder import (
    build_node_index,
    build_nodes,
    compute_output_vector,
    create_dense_memmap,
    write_build_report,
    write_flows_to_dense_matrix,
)
from climate_risk_io.sam.mappings import (
    COLUMNS_EXCLUDED,
    MATERIALIZED_AT_COLUMN,
    SAM_COLUMN_CONFIG,
    SAM_TABLE,
)
from config.paths import SAM_PROCESSED_DIR


# --- Filters -----------------------------------------------------------------
FILTER_MATRIX_ID = 'mrsam_euita_2022_3oe'
FILTER_TIME_PERIOD = 2022
FILTER_LATEST_MATERIALIZATION = True

# Columns used to build the matrix, in standardized internal names.
COLUMNS_USED = [
    "matrix_id",
    "origin_region",
    "origin_sector",
    "destination_region",
    "destination_sector",
    "flow_value",
    "time_period",
    "row_label",
    "col_label",
]

GROUP_KEYS = [
    "origin_region",
    "origin_sector",
    "destination_region",
    "destination_sector",
]

ORIENTATION = "rows = supplier/origin nodes; columns = buyer/destination nodes"


def select_and_standardize(df):
    cols = SAM_COLUMN_CONFIG
    return df.select(
        F.col(cols["matrix_id"]).alias("matrix_id"),
        F.col(cols["origin_region"]).alias("origin_region"),
        F.col(cols["origin_sector"]).alias("origin_sector"),
        F.col(cols["destination_region"]).alias("destination_region"),
        F.col(cols["destination_sector"]).alias("destination_sector"),
        F.col(cols["flow_value"]).alias("flow_value"),
        F.col(cols["time_period"]).alias("time_period"),
        F.col(cols["row_label"]).alias("row_label"),
        F.col(cols["col_label"]).alias("col_label"),
    )


def apply_filters(df):
    cols = SAM_COLUMN_CONFIG
    if FILTER_MATRIX_ID is not None:
        df = df.filter(F.col(cols["matrix_id"]) == FILTER_MATRIX_ID)
    if FILTER_TIME_PERIOD is not None:
        df = df.filter(F.col(cols["time_period"]) == FILTER_TIME_PERIOD)
    if FILTER_LATEST_MATERIALIZATION:
        latest = df.agg(
            F.max(MATERIALIZED_AT_COLUMN).alias("latest")
        ).collect()[0]["latest"]
        if latest is None:
            raise ValueError("No materialized_at value found after filters.")
        print(f"Using latest materialized_at: {latest}")
        df = df.filter(F.col(MATERIALIZED_AT_COLUMN) == latest)
    return df


def main() -> None:
    print("\n=== Build Dense SAM Matrix From Databricks ===")
    print(f"Source table: {SAM_TABLE}")
    print(f"FILTER_MATRIX_ID: {FILTER_MATRIX_ID}")
    print(f"FILTER_TIME_PERIOD: {FILTER_TIME_PERIOD}")
    print(f"FILTER_LATEST_MATERIALIZATION: {FILTER_LATEST_MATERIALIZATION}")

    raw = apply_filters(read_sam_table())
    flows = select_and_standardize(raw)

    # Null flow values cannot be placed in a numeric cell; drop them from the
    # matrix fill but report their count. Small/zero/negative values are kept.
    null_flow_count = flows.filter(F.col("flow_value").isNull()).count()
    flows = flows.filter(F.col("flow_value").isNotNull())

    if flows.limit(1).count() == 0:
        raise ValueError("SAM extract is empty after filters.")

    # Aggregate duplicate origin->destination pairs on the cluster.
    aggregated = flows.groupBy(*GROUP_KEYS).agg(
        F.sum("flow_value").alias("flow_value")
    )

    # --- Source flow statistics (single cluster-side pass) -------------------
    stats = flows.agg(
        F.sum("flow_value").alias("total_flow_value"),
        F.min("flow_value").alias("min_flow_value"),
        F.max("flow_value").alias("max_flow_value"),
        F.sum(F.when(F.col("flow_value") < 0, 1).otherwise(0)).alias("neg"),
        F.sum(F.when(F.col("flow_value") == 0, 1).otherwise(0)).alias("zero"),
    ).collect()[0]

    matrix_id_values = sorted(
        r["matrix_id"] for r in flows.select("matrix_id").distinct().collect()
    )
    time_period_values = sorted(
        r["time_period"] for r in flows.select("time_period").distinct().collect()
    )

    # --- Node universe -------------------------------------------------------
    # The macrosector is the third "__"-separated part of the account label
    # (row_label for origins, col_label for destinations). It is needed by the
    # modelling layer to classify accounts into productive / final-demand /
    # value-added blocks, so it is carried into the node table here.
    print("\nBuilding node universe...")
    origins = flows.select(
        F.col("origin_region").alias("region_code"),
        F.col("origin_sector").alias("sector_code"),
        F.element_at(F.split(F.col("row_label"), "__"), 3).alias("macrosector_code"),
    )
    destinations = flows.select(
        F.col("destination_region").alias("region_code"),
        F.col("destination_sector").alias("sector_code"),
        F.element_at(F.split(F.col("col_label"), "__"), 3).alias("macrosector_code"),
    )
    pairs_pdf = origins.union(destinations).distinct().toPandas()
    nodes = build_nodes(pairs_pdf)
    node_index = build_node_index(nodes)
    n_nodes = len(nodes)

    matrix_bytes = n_nodes * n_nodes * np.dtype(np.float64).itemsize
    print(f"Nodes: {n_nodes:,}")
    print(
        f"Dense matrix size: {n_nodes} x {n_nodes} float64 "
        f"= {matrix_bytes / (1024 ** 3):.2f} GB on disk"
    )

    # --- Dense matrix ---------------------------------------------------------
    SAM_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    z_path = SAM_PROCESSED_DIR / "z_matrix.npy"
    x_path = SAM_PROCESSED_DIR / "x_vector.npy"
    nodes_path = SAM_PROCESSED_DIR / "nodes.csv"
    province_mapping_path = SAM_PROCESSED_DIR / "province_mapping.csv"
    sector_mapping_path = SAM_PROCESSED_DIR / "sector_mapping.csv"
    report_path = SAM_PROCESSED_DIR / "sam_build_report.json"

    print(f"\nAllocating dense memmap: {z_path}")
    Z = create_dense_memmap(z_path, n_nodes)

    # Fill in chunks by origin region to keep each collect small.
    region_values = sorted(
        r["origin_region"]
        for r in aggregated.select("origin_region").distinct().collect()
    )
    print(f"Filling matrix in {len(region_values)} origin-region chunks...")
    cells_written = 0
    for idx, region in enumerate(region_values, start=1):
        chunk = aggregated.filter(F.col("origin_region") == region).toPandas()
        cells_written += write_flows_to_dense_matrix(Z, chunk, node_index)
        print(f"  [{idx}/{len(region_values)}] {region}: {len(chunk):,} cells")
    Z.flush()

    # --- Output vector --------------------------------------------------------
    print("\nComputing output vector x[i] = sum_j Z[i, j]...")
    x = compute_output_vector(Z)
    np.save(x_path, x)

    # --- Node / mapping tables ------------------------------------------------
    nodes.to_csv(nodes_path, index=False)
    (
        nodes[["region_code"]]
        .drop_duplicates()
        .sort_values("region_code")
        .reset_index(drop=True)
        .to_csv(province_mapping_path, index=False)
    )
    (
        nodes[["sector_code"]]
        .drop_duplicates()
        .sort_values("sector_code")
        .reset_index(drop=True)
        .to_csv(sector_mapping_path, index=False)
    )

    # --- Build report ---------------------------------------------------------
    report = {
        "table_name": SAM_TABLE,
        "filters_applied": {
            "matrix_id": FILTER_MATRIX_ID,
            "time_period": FILTER_TIME_PERIOD,
            "latest_materialization": FILTER_LATEST_MATERIALIZATION,
        },
        "columns_used": COLUMNS_USED,
        "columns_excluded": COLUMNS_EXCLUDED,
        "n_nodes": int(n_nodes),
        "matrix_shape": [int(n_nodes), int(n_nodes)],
        "dtype": "float64",
        "total_flow_value": float(stats["total_flow_value"]),
        "min_flow_value": float(stats["min_flow_value"]),
        "max_flow_value": float(stats["max_flow_value"]),
        "negative_flow_count": int(stats["neg"]),
        "zero_flow_count": int(stats["zero"]),
        "null_flow_count": int(null_flow_count),
        "matrix_id_values": matrix_id_values,
        "time_period_values": time_period_values,
        "outputs_written": {
            "nodes": str(nodes_path),
            "z_matrix": str(z_path),
            "x_vector": str(x_path),
            "province_mapping": str(province_mapping_path),
            "sector_mapping": str(sector_mapping_path),
            "sam_build_report": str(report_path),
        },
        "orientation": ORIENTATION,
    }
    write_build_report(report_path, report)

    z_total = float(Z.sum())
    print("\n=== Build Complete ===")
    print(f"Nodes: {n_nodes:,}")
    print(f"Z shape: ({n_nodes}, {n_nodes})")
    print(f"Cells written: {cells_written:,}")
    print(f"Z.sum(): {z_total}")
    print(f"sum(x): {float(x.sum())}")
    print(f"Source total_flow_value: {report['total_flow_value']}")
    print(f"Null flow rows dropped: {null_flow_count:,}")
    print(f"Matrix convention: Z[i, j] = flow from supplier node i to buyer node j.")


if __name__ == "__main__":
    main()
