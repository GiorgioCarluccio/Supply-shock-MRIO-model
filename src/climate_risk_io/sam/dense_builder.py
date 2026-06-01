"""Build the dense SAM matrix and its node table.

The matrix convention is::

    Z[i, j] = flow from supplier node i to buyer node j

Rows are supplier/origin nodes; columns are buyer/destination nodes.

The matrix is materialized as a memory-mapped float64 ``.npy`` file so it never
has to fit in RAM in full. Flows are written into it in chunks by the caller.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def build_nodes(pairs_df: pd.DataFrame) -> pd.DataFrame:
    """Build the deterministic region-sector node universe.

    ``pairs_df`` must hold the (already de-duplicated) union of origin and
    destination region/sector pairs in columns ``region_code`` and
    ``sector_code``. Node IDs are assigned after sorting by region then sector.

    If ``pairs_df`` also carries a ``macrosector_code`` column (the third,
    ``__``-separated part of the source ``row_label``/``col_label``), it is kept
    and the canonical three-part ``region__sector__macrosector`` ``node_label``
    is emitted. The macrosector is needed downstream to classify accounts into
    productive / final-demand / value-added blocks. When the column is absent
    the legacy two-part label is produced for backward compatibility.
    """
    has_macro = "macrosector_code" in pairs_df.columns
    keep = ["region_code", "sector_code"] + (["macrosector_code"] if has_macro else [])

    nodes = (
        pairs_df[keep]
        .drop_duplicates()
        .sort_values(["region_code", "sector_code"], kind="mergesort")
        .reset_index(drop=True)
    )
    nodes.insert(0, "node_id", np.arange(len(nodes), dtype=np.int64))

    if has_macro:
        nodes["node_label"] = (
            nodes["region_code"].astype(str)
            + "__"
            + nodes["sector_code"].astype(str)
            + "__"
            + nodes["macrosector_code"].astype(str)
        )
        return nodes[
            ["node_id", "region_code", "sector_code", "macrosector_code", "node_label"]
        ]

    nodes["node_label"] = (
        nodes["region_code"].astype(str) + "__" + nodes["sector_code"].astype(str)
    )
    return nodes[["node_id", "region_code", "sector_code", "node_label"]]


def build_node_index(nodes_df: pd.DataFrame) -> dict:
    """Map (region_code, sector_code) -> node_id for fast lookup."""
    return {
        (row.region_code, row.sector_code): int(row.node_id)
        for row in nodes_df.itertuples(index=False)
    }


def create_dense_memmap(path: Path, n_nodes: int, dtype=np.float64):
    """Create a zero-initialized, disk-backed dense matrix of shape (n, n)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # open_memmap creates a file sized for the full array; new file space is
    # zero-filled by the OS, which is exactly the desired initial state.
    return np.lib.format.open_memmap(
        path, mode="w+", dtype=dtype, shape=(n_nodes, n_nodes)
    )


def write_flows_to_dense_matrix(
    Z, flows_df: pd.DataFrame, node_index: dict
) -> int:
    """Write a chunk of standardized flows into the dense matrix.

    ``flows_df`` must have columns ``origin_region``, ``origin_sector``,
    ``destination_region``, ``destination_sector`` and ``flow_value``. Returns
    the number of cells written.
    """
    if flows_df.empty:
        return 0

    row_idx = np.fromiter(
        (
            node_index[(r, s)]
            for r, s in zip(flows_df["origin_region"], flows_df["origin_sector"])
        ),
        dtype=np.int64,
        count=len(flows_df),
    )
    col_idx = np.fromiter(
        (
            node_index[(r, s)]
            for r, s in zip(
                flows_df["destination_region"], flows_df["destination_sector"]
            )
        ),
        dtype=np.int64,
        count=len(flows_df),
    )
    values = flows_df["flow_value"].to_numpy(dtype=np.float64)

    # Accumulate so repeated (i, j) pairs sum rather than overwrite.
    np.add.at(Z, (row_idx, col_idx), values)
    return len(flows_df)


def compute_output_vector(Z) -> np.ndarray:
    """Compute x[i] = sum_j Z[i, j] for each supplier node."""
    return np.asarray(Z.sum(axis=1), dtype=np.float64).ravel()


def write_build_report(path: Path, report: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
