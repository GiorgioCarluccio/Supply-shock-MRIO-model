"""DEPRECATED. Build node tables, sparse SAM matrices, and output vectors.

The SAM has no truly zero entries and small values are meaningful, so a sparse
representation is not appropriate. Use ``climate_risk_io.sam.dense_builder`` and
``scripts/build_sam_dense_matrix_from_databricks.py`` instead. This module is
retained only for backward compatibility.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse

FLOW_KEY_COLUMNS = [
    "origin_region",
    "origin_sector",
    "destination_region",
    "destination_sector",
]


def aggregate_flows(flows_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate duplicate origin-destination node pairs."""
    return (
        flows_df.groupby(FLOW_KEY_COLUMNS, as_index=False, dropna=False)["flow_value"]
        .sum()
        .sort_values(FLOW_KEY_COLUMNS)
        .reset_index(drop=True)
    )


def build_nodes(flows_df: pd.DataFrame) -> pd.DataFrame:
    """Build the deterministic region-sector node universe."""
    origin_nodes = flows_df[["origin_region", "origin_sector"]].rename(
        columns={"origin_region": "region_code", "origin_sector": "sector_code"}
    )
    destination_nodes = flows_df[
        ["destination_region", "destination_sector"]
    ].rename(
        columns={
            "destination_region": "region_code",
            "destination_sector": "sector_code",
        }
    )

    nodes = (
        pd.concat([origin_nodes, destination_nodes], ignore_index=True)
        .drop_duplicates()
        .sort_values(["region_code", "sector_code"], kind="mergesort")
        .reset_index(drop=True)
    )
    nodes.insert(0, "node_id", np.arange(len(nodes), dtype=np.int64))
    nodes["node_label"] = (
        nodes["region_code"].astype(str) + "__" + nodes["sector_code"].astype(str)
    )
    return nodes[["node_id", "region_code", "sector_code", "node_label"]]


def build_sparse_z_matrix(flows_df: pd.DataFrame, nodes_df: pd.DataFrame):
    """Build CSR Z where rows are suppliers and columns are buyers."""
    node_lookup = {
        (row.region_code, row.sector_code): int(row.node_id)
        for row in nodes_df.itertuples(index=False)
    }

    row_index = [
        node_lookup[(row.origin_region, row.origin_sector)]
        for row in flows_df.itertuples(index=False)
    ]
    col_index = [
        node_lookup[(row.destination_region, row.destination_sector)]
        for row in flows_df.itertuples(index=False)
    ]
    values = flows_df["flow_value"].to_numpy(dtype=float)

    shape = (len(nodes_df), len(nodes_df))
    return sparse.coo_matrix((values, (row_index, col_index)), shape=shape).tocsr()


def build_output_vector(Z, nodes_df: pd.DataFrame) -> pd.DataFrame:
    """Compute x[i] = sum_j Z[i, j] for each supplier node."""
    x_output = np.asarray(Z.sum(axis=1)).ravel()
    x = nodes_df.copy()
    x["x_output"] = x_output
    return x[["node_id", "region_code", "sector_code", "node_label", "x_output"]]

