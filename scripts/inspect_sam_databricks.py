import sys
from pathlib import Path

from pyspark.sql import functions as F


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from climate_risk_io.sam.databricks_client import read_sam_table
from climate_risk_io.sam.mappings import (
    MATERIALIZED_AT_COLUMN,
    SAM_COLUMN_CONFIG,
    SAM_TABLE,
)


def show_group_counts(df, column_name: str, title: str) -> None:
    print(f"\n=== {title} ===")
    (
        df.groupBy(column_name)
        .count()
        .orderBy(F.col(column_name).asc_nulls_last())
        .show(100, truncate=False)
    )


def main() -> None:
    print("\n=== SAM Databricks Table Inspection ===")
    print(f"Table path: {SAM_TABLE}")

    df = read_sam_table()
    cols = SAM_COLUMN_CONFIG

    print("\n=== Schema ===")
    df.printSchema()

    print("\n=== Sample Rows ===")
    df.limit(10).show(10, truncate=False)

    print("\n=== Row Count ===")
    row_count = df.count()
    print(f"Rows: {row_count:,}")

    show_group_counts(df, cols["matrix_id"], "matrix_id values and row counts")
    show_group_counts(df, cols["time_period"], "time_period values and row counts")

    print("\n=== Summary Metrics ===")
    summary = df.agg(
        F.countDistinct(cols["origin_region"]).alias("unique_origin_regions"),
        F.countDistinct(cols["destination_region"]).alias(
            "unique_destination_regions"
        ),
        F.countDistinct(cols["origin_sector"]).alias("unique_origin_sectors"),
        F.countDistinct(cols["destination_sector"]).alias(
            "unique_destination_sectors"
        ),
        F.sum(cols["flow_value"]).alias("total_flow_value"),
        F.min(cols["flow_value"]).alias("min_flow_value"),
        F.max(cols["flow_value"]).alias("max_flow_value"),
        F.sum(F.when(F.col(cols["flow_value"]).isNull(), 1).otherwise(0)).alias(
            "null_value_rows"
        ),
        F.sum(F.when(F.col(cols["flow_value"]) == 0, 1).otherwise(0)).alias(
            "zero_value_rows"
        ),
        F.sum(F.when(F.col(cols["flow_value"]) < 0, 1).otherwise(0)).alias(
            "negative_value_rows"
        ),
        F.sum(
            F.when(
                F.col(cols["origin_region"]).isNull()
                | F.col(cols["origin_sector"]).isNull()
                | F.col(cols["destination_region"]).isNull()
                | F.col(cols["destination_sector"]).isNull(),
                1,
            ).otherwise(0)
        ).alias("null_origin_destination_code_rows"),
        F.max(cols["time_period"]).alias("latest_time_period"),
        F.max(MATERIALIZED_AT_COLUMN).alias("latest_materialized_at"),
    ).collect()[0]

    for key, value in summary.asDict().items():
        print(f"{key}: {value}")

    print("\n=== Recommended Extraction Filter Options ===")
    print(f"Latest time_period available: {summary['latest_time_period']}")
    print(f"Latest materialized_at available: {summary['latest_materialized_at']}")
    print(
        "If multiple matrix_id values are shown above, choose the intended matrix_id "
        "before extraction."
    )
    print(
        "Set FILTER_MATRIX_ID, FILTER_TIME_PERIOD, and "
        "FILTER_LATEST_MATERIALIZATION in scripts/extract_sam_from_databricks.py."
    )


if __name__ == "__main__":
    main()
