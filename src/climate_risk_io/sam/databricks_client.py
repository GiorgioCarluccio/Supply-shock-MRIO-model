"""Small Databricks Connect helpers for reading the SAM source table."""

from __future__ import annotations

from dotenv import load_dotenv

from climate_risk_io.sam.mappings import SAM_TABLE


def _load_auth_env() -> None:
    """Load Databricks authentication environment variables.

    Loads the project ``.env`` first, then the Databricks VS Code extension's
    generated ``.databricks/.databricks.env`` (if present) without overriding
    anything already set. The extension keeps that file pointed at a local
    metadata service while it is running, so a plain terminal can reuse the same
    authentication the extension provides to notebooks.

    For headless / CI runs where the extension is not running, configure a
    profile (``databricks auth login``) or a PAT via ``.env`` instead.
    """
    load_dotenv()
    try:
        from config.paths import PROJECT_ROOT

        ext_env = PROJECT_ROOT / ".databricks" / ".databricks.env"
        if ext_env.exists():
            load_dotenv(ext_env, override=False)
    except Exception:
        # Auth env loading is best-effort; the SDK will raise a clear error
        # later if no usable credentials are found.
        pass


def get_spark_session():
    """Create or retrieve a Spark session configured by Databricks Connect."""
    _load_auth_env()

    try:
        from databricks.connect import DatabricksSession
    except ImportError:
        from pyspark.sql import SparkSession

        return SparkSession.builder.getOrCreate()

    print(
        "Connecting to Databricks Connect (serverless cold start can take "
        "~30-90s the first time; do not interrupt)...",
        flush=True,
    )
    spark = DatabricksSession.builder.getOrCreate()
    print("Connected to Databricks.", flush=True)
    return spark


def read_sam_table(spark=None, table_name: str = SAM_TABLE):
    """Return a Spark DataFrame reference for the SAM table."""
    if spark is None:
        spark = get_spark_session()
    return spark.table(table_name)

