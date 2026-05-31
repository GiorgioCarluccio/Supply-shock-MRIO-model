"""Reusable validation helpers for SAM inputs and outputs."""

from __future__ import annotations

import numpy as np
import pandas as pd

try:  # scipy is only needed by the deprecated sparse workflow.
    from scipy import sparse
except ImportError:  # pragma: no cover
    sparse = None


def validate_required_columns(df: pd.DataFrame, required_columns) -> None:
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def validate_no_nulls(df: pd.DataFrame, columns) -> None:
    null_counts = {
        column: int(df[column].isna().sum())
        for column in columns
        if column in df.columns and df[column].isna().any()
    }
    if null_counts:
        raise ValueError(f"Unexpected null values: {null_counts}")


def validate_non_empty(df: pd.DataFrame, name: str) -> None:
    if df.empty:
        raise ValueError(f"{name} is empty.")


def validate_dense_model_outputs(nodes: pd.DataFrame, Z, x) -> None:
    """Validate the dense-matrix model outputs (nodes, dense Z, x vector).

    ``Z`` is a dense NumPy array (possibly a memmap). ``x`` may be a 1-D NumPy
    array or a DataFrame/Series with an ``x_output`` column.
    """
    validate_non_empty(nodes, "nodes")
    validate_required_columns(
        nodes,
        ["node_id", "region_code", "sector_code", "node_label"],
    )
    validate_no_nulls(nodes, ["node_id", "region_code", "sector_code"])

    if not isinstance(Z, np.ndarray):
        raise ValueError("Z must be a NumPy array (dense matrix).")
    if Z.ndim != 2 or Z.shape[0] != Z.shape[1]:
        raise ValueError(f"Z must be square 2-D, got shape {Z.shape}.")
    if Z.shape[0] != len(nodes):
        raise ValueError(
            f"Z dimension {Z.shape[0]} does not match node count {len(nodes)}."
        )

    if isinstance(x, pd.DataFrame):
        x_values = x["x_output"].to_numpy(dtype=float)
    elif isinstance(x, pd.Series):
        x_values = x.to_numpy(dtype=float)
    else:
        x_values = np.asarray(x, dtype=float).ravel()

    if len(x_values) != len(nodes):
        raise ValueError(
            f"x length {len(x_values)} does not match node count {len(nodes)}."
        )
    if not nodes["node_id"].is_unique:
        raise ValueError("node_id values must be unique.")

    z_sum = float(Z.sum())
    x_sum = float(x_values.sum())
    if not np.isclose(z_sum, x_sum, rtol=1e-9, atol=1e-6):
        raise ValueError(f"sum(x) {x_sum} does not match Z.sum() {z_sum}.")


def validate_model_outputs(nodes: pd.DataFrame, Z, x: pd.DataFrame) -> None:
    validate_non_empty(nodes, "nodes")
    validate_non_empty(x, "x vector")
    validate_required_columns(
        nodes,
        ["node_id", "region_code", "sector_code", "node_label"],
    )
    validate_required_columns(x, ["node_id", "x_output"])
    validate_no_nulls(nodes, ["node_id", "region_code", "sector_code"])

    if sparse is None or not sparse.issparse(Z):
        raise ValueError("Z must be a scipy sparse matrix.")
    if Z.shape[0] != Z.shape[1]:
        raise ValueError(f"Z must be square, got shape {Z.shape}.")
    if Z.shape[0] != len(nodes):
        raise ValueError(
            f"Z dimension {Z.shape[0]} does not match node count {len(nodes)}."
        )
    if len(x) != len(nodes):
        raise ValueError(f"x length {len(x)} does not match node count {len(nodes)}.")
    if not nodes["node_id"].is_unique:
        raise ValueError("node_id values must be unique.")

    z_sum = float(Z.sum())
    x_sum = float(x["x_output"].sum())
    if z_sum <= 0:
        raise ValueError(f"Total flow value must be positive, got {z_sum}.")
    if not np.isclose(z_sum, x_sum, rtol=1e-9, atol=1e-6):
        raise ValueError(f"sum(x_output) {x_sum} does not match Z.sum() {z_sum}.")

