"""Build model-ready inputs from the existing dense SAM artifact.

The dense SAM artifact (``data/processed/sam/``) provides:

* ``nodes.csv`` : node table with ``node_id``, ``region_code``, ``sector_code``
  and (after the macrosector-aware ingestion fix) ``macrosector_code``.
* ``z_matrix.npy`` : dense (N, N) flow matrix, rows = seller, columns = buyer.
* ``x_vector.npy`` : (N,) row-output vector (= row sums of the full matrix).

This module slices the **productive block** out of the full SAM and writes the
clean arrays the propagation model consumes:

    Z0  = productive rows x productive columns
    FD0 = productive rows x final-demand columns, summed per productive row
    VA0 = value-added rows x productive columns
    IMP0 = import/external rows x productive columns
    X0  = row_sum(Z0) + FD0

Node ordering is deterministic: productive nodes are ordered by
``region_code`` then ``sector_code`` ascending, and that order is shared by all
arrays and CSV outputs.

Macrosector requirement
------------------------
The split into productive / final-demand / value-added accounts is driven by
the macrosector code. If ``nodes.csv`` lacks macrosector information (no
``macrosector_code`` column and a two-part ``node_label``), the builder raises a
clear error explaining that the SAM artifact must be rebuilt with full account
labels (see ``scripts/build_sam_dense_matrix_from_databricks.py``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from . import label_parser
from .label_parser import (
    FINAL_DEMAND,
    PRODUCTIVE,
    VALUE_ADDED,
    build_label,
    classify_account,
)

# ROW is final demand on the column side (exports) and an external/import input
# on the row side when it sells into productive columns.
EXTERNAL_INPUT_MACROSECTORS = frozenset({"R"})


# --------------------------------------------------------------------------- #
# 1) Load the SAM artifact
# --------------------------------------------------------------------------- #
def load_full_sam_artifact(sam_dir: Path, mmap: bool = False) -> Dict[str, Any]:
    """Load the dense SAM artifact (nodes table, Z matrix, x vector).

    Parameters
    ----------
    sam_dir:
        Directory holding ``nodes.csv``, ``z_matrix.npy`` and ``x_vector.npy``.
    mmap:
        If True, memory-map the matrix instead of loading it into RAM.
    """
    sam_dir = Path(sam_dir)
    nodes_path = sam_dir / "nodes.csv"
    z_path = sam_dir / "z_matrix.npy"
    x_path = sam_dir / "x_vector.npy"

    for path in (nodes_path, z_path, x_path):
        if not path.exists():
            raise FileNotFoundError(f"Required SAM artifact not found: {path}")

    nodes = pd.read_csv(nodes_path)
    Z = np.load(z_path, mmap_mode="r") if mmap else np.load(z_path)
    x = np.load(x_path)
    return {"nodes": nodes, "Z": Z, "x": x, "sam_dir": sam_dir}


# --------------------------------------------------------------------------- #
# 2) Account metadata + classification masks
# --------------------------------------------------------------------------- #
def _resolve_macrosector(nodes: pd.DataFrame) -> pd.Series:
    """Return a macrosector_code Series, deriving it from labels if needed.

    Resolution order:
    1. an explicit ``macrosector_code`` column;
    2. a three-part ``node_label`` (``region__sector__macrosector``).

    Raises a clear error if neither source is available.
    """
    if "macrosector_code" in nodes.columns and nodes["macrosector_code"].notna().all():
        return nodes["macrosector_code"].astype(str)

    if "node_label" in nodes.columns:
        parts = nodes["node_label"].astype(str).str.split("__", expand=True)
        if parts.shape[1] == 3 and parts[2].notna().all():
            return parts[2].astype(str)

    raise ValueError(
        "Cannot determine account macrosector. The SAM nodes table is missing "
        "macrosector information: it has neither a 'macrosector_code' column nor "
        "a three-part 'region__sector__macrosector' node_label. Rebuild the SAM "
        "artifact with full account labels (row_label/col_label carry the "
        "macrosector as their third '__'-separated part) by running "
        "scripts/build_sam_dense_matrix_from_databricks.py."
    )


def build_account_metadata(nodes: pd.DataFrame) -> pd.DataFrame:
    """Augment the node table with macrosector, classification and masks.

    Returns a copy of ``nodes`` with added columns:
    ``macrosector_code``, ``account_class``, ``full_label``,
    ``is_productive_account``, ``is_final_demand_account``,
    ``is_value_added_account``, ``is_external_input_account``,
    ``is_institutional_account``.
    """
    required = {"node_id", "region_code", "sector_code"}
    missing = required - set(nodes.columns)
    if missing:
        raise ValueError(f"nodes table is missing required columns: {sorted(missing)}")

    meta = nodes.copy().reset_index(drop=True)
    meta["macrosector_code"] = _resolve_macrosector(meta).to_numpy()

    meta["full_label"] = [
        build_label(r, s, m)
        for r, s, m in zip(
            meta["region_code"].astype(str),
            meta["sector_code"].astype(str),
            meta["macrosector_code"].astype(str),
        )
    ]
    meta["account_class"] = [
        classify_account({"macrosector_code": m})
        for m in meta["macrosector_code"].astype(str)
    ]

    meta["is_productive_account"] = meta["account_class"] == PRODUCTIVE
    meta["is_final_demand_account"] = meta["account_class"] == FINAL_DEMAND
    meta["is_value_added_account"] = meta["account_class"] == VALUE_ADDED
    meta["is_external_input_account"] = meta["macrosector_code"].astype(str).isin(
        EXTERNAL_INPUT_MACROSECTORS
    )
    meta["is_institutional_account"] = ~meta["is_productive_account"]
    return meta


def _ordered_indices(meta: pd.DataFrame, mask_col: str) -> np.ndarray:
    """Return SAM row indices for a mask, ordered by (region, sector) asc.

    The returned positions index into the SAM matrix (they equal the position
    of each row in ``meta``, which is aligned with the matrix by construction).
    """
    subset = meta[meta[mask_col]].copy()
    subset = subset.sort_values(
        ["region_code", "sector_code"], kind="mergesort"
    )
    return subset.index.to_numpy()


# --------------------------------------------------------------------------- #
# 3) Block builders
# --------------------------------------------------------------------------- #
def build_productive_block(Z: np.ndarray, productive_idx: np.ndarray) -> np.ndarray:
    """``Z0`` = productive rows x productive columns."""
    return np.asarray(Z[np.ix_(productive_idx, productive_idx)], dtype=float)


def build_final_demand_vector(
    Z: np.ndarray, productive_idx: np.ndarray, final_demand_idx: np.ndarray
) -> np.ndarray:
    """``FD0[i]`` = sum over final-demand columns of productive row ``i``."""
    block = np.asarray(Z[np.ix_(productive_idx, final_demand_idx)], dtype=float)
    return block.sum(axis=1)


def build_value_added_block(
    Z: np.ndarray, value_added_idx: np.ndarray, productive_idx: np.ndarray
) -> np.ndarray:
    """``VA0`` = value-added rows x productive columns."""
    return np.asarray(Z[np.ix_(value_added_idx, productive_idx)], dtype=float)


def build_external_input_block(
    Z: np.ndarray, external_input_idx: np.ndarray, productive_idx: np.ndarray
) -> np.ndarray:
    """``IMP0`` = external/import rows x productive columns."""
    return np.asarray(Z[np.ix_(external_input_idx, productive_idx)], dtype=float)


def build_output_vector(Z0: np.ndarray, FD0: np.ndarray) -> np.ndarray:
    """``X0[i]`` = row_sum(Z0[i, :]) + FD0[i]."""
    return Z0.sum(axis=1) + np.asarray(FD0, dtype=float).reshape(-1)


def build_globsec_mapping(productive_meta: pd.DataFrame):
    """Build the sector-group mapping for the productive nodes.

    Returns ``(globsec_of, sector_mapping_df)`` where ``globsec_of[k]`` is the
    integer sector-group id of productive node ``k`` (in productive order) and
    ``sector_mapping_df`` has columns ``sector_group_id``, ``sector_code``,
    ``macrosector_code``. Sector groups are the productive sector codes, ordered
    ascending, with ids starting at 0.
    """
    sector_codes = productive_meta["sector_code"].astype(str)
    unique_sectors = sorted(sector_codes.unique())
    sector_to_id = {code: i for i, code in enumerate(unique_sectors)}

    globsec_of = sector_codes.map(sector_to_id).to_numpy(dtype=np.int64)

    macro_by_sector = (
        productive_meta.drop_duplicates("sector_code")
        .set_index("sector_code")["macrosector_code"]
        .astype(str)
    )
    sector_mapping = pd.DataFrame(
        {
            "sector_group_id": [sector_to_id[c] for c in unique_sectors],
            "sector_code": unique_sectors,
            "macrosector_code": [macro_by_sector[c] for c in unique_sectors],
        }
    )
    return globsec_of, sector_mapping


# --------------------------------------------------------------------------- #
# 4) Column-side accounting diagnostics
# --------------------------------------------------------------------------- #
def compute_accounting_diagnostics(
    Z0: np.ndarray, VA0: np.ndarray, X0: np.ndarray, IMP0: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """Compute the row-vs-column output reconciliation diagnostics."""
    intermediate_inputs_by_column = Z0.sum(axis=0)
    value_added_by_column = VA0.sum(axis=0)
    import_inputs_by_column = (
        np.asarray(IMP0, dtype=float).sum(axis=0)
        if IMP0 is not None
        else np.zeros_like(intermediate_inputs_by_column)
    )
    X0_column_check_va_only = intermediate_inputs_by_column + value_added_by_column
    X0_column_check = X0_column_check_va_only + import_inputs_by_column
    gap = X0 - X0_column_check
    gap_va_only = X0 - X0_column_check_va_only

    abs_gap = np.abs(gap)
    denom = np.where(np.abs(X0) > 1e-12, np.abs(X0), np.nan)
    rel_error = np.abs(gap) / denom
    rel_error = np.nan_to_num(rel_error, nan=0.0)
    abs_gap_va_only = np.abs(gap_va_only)
    rel_error_va_only = np.abs(gap_va_only) / denom
    rel_error_va_only = np.nan_to_num(rel_error_va_only, nan=0.0)

    return {
        "max_abs_gap": float(abs_gap.max()),
        "mean_abs_gap": float(abs_gap.mean()),
        "max_rel_error": float(rel_error.max()),
        "total_row_output": float(X0.sum()),
        "total_column_output": float(X0_column_check.sum()),
        "total_import_inputs": float(import_inputs_by_column.sum()),
        "va_only": {
            "max_abs_gap": float(abs_gap_va_only.max()),
            "mean_abs_gap": float(abs_gap_va_only.mean()),
            "max_rel_error": float(rel_error_va_only.max()),
            "total_column_output": float(X0_column_check_va_only.sum()),
        },
    }


# --------------------------------------------------------------------------- #
# 5) Writers
# --------------------------------------------------------------------------- #
def write_model_inputs(
    out_dir: Path,
    productive_nodes: pd.DataFrame,
    account_nodes: pd.DataFrame,
    Z0: np.ndarray,
    FD0: np.ndarray,
    X0: np.ndarray,
    VA0: np.ndarray,
    IMP0: np.ndarray,
    globsec_of: np.ndarray,
    sector_mapping: pd.DataFrame,
    report: Dict[str, Any],
    A0: Optional[np.ndarray] = None,
) -> Dict[str, str]:
    """Write all model-ready artifacts to ``out_dir`` and return their paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    paths: Dict[str, str] = {}

    productive_nodes.to_csv(out_dir / "productive_nodes.csv", index=False)
    paths["productive_nodes"] = str(out_dir / "productive_nodes.csv")
    account_nodes.to_csv(out_dir / "account_nodes.csv", index=False)
    paths["account_nodes"] = str(out_dir / "account_nodes.csv")
    sector_mapping.to_csv(out_dir / "sector_mapping.csv", index=False)
    paths["sector_mapping"] = str(out_dir / "sector_mapping.csv")

    np.save(out_dir / "Z0.npy", Z0)
    paths["Z0"] = str(out_dir / "Z0.npy")
    np.save(out_dir / "FD0.npy", FD0)
    paths["FD0"] = str(out_dir / "FD0.npy")
    np.save(out_dir / "X0.npy", X0)
    paths["X0"] = str(out_dir / "X0.npy")
    np.save(out_dir / "VA0.npy", VA0)
    paths["VA0"] = str(out_dir / "VA0.npy")
    np.save(out_dir / "IMP0.npy", IMP0)
    paths["IMP0"] = str(out_dir / "IMP0.npy")
    np.save(out_dir / "globsec_of.npy", globsec_of)
    paths["globsec_of"] = str(out_dir / "globsec_of.npy")

    if A0 is not None:
        np.save(out_dir / "A0.npy", A0)
        paths["A0"] = str(out_dir / "A0.npy")

    with (out_dir / "model_input_report.json").open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
    paths["model_input_report"] = str(out_dir / "model_input_report.json")

    return paths


# --------------------------------------------------------------------------- #
# 6) Orchestrator
# --------------------------------------------------------------------------- #
def build_model_inputs(
    sam_dir: Path,
    out_dir: Path,
    *,
    write: bool = True,
    save_a0: bool = False,
    mmap: bool = False,
) -> Dict[str, Any]:
    """Build (and optionally write) all model inputs from the SAM artifact.

    Returns a dict holding the in-memory arrays, the node tables, the sector
    mapping and the build report.
    """
    sam_dir = Path(sam_dir)
    out_dir = Path(out_dir)

    artifact = load_full_sam_artifact(sam_dir, mmap=mmap)
    Z = artifact["Z"]
    nodes = artifact["nodes"]

    meta = build_account_metadata(nodes)

    productive_idx = _ordered_indices(meta, "is_productive_account")
    final_demand_idx = _ordered_indices(meta, "is_final_demand_account")
    value_added_idx = _ordered_indices(meta, "is_value_added_account")
    external_input_idx = _ordered_indices(meta, "is_external_input_account")

    if productive_idx.size == 0:
        raise ValueError("No productive accounts found in the SAM artifact.")
    if final_demand_idx.size == 0:
        raise ValueError("No final-demand accounts found in the SAM artifact.")

    # Productive node table in deterministic (region, sector) order.
    productive_meta = meta.loc[productive_idx].reset_index(drop=True)
    productive_nodes = pd.DataFrame(
        {
            "node_id": np.arange(len(productive_meta), dtype=np.int64),
            "region_code": productive_meta["region_code"].astype(str),
            "sector_code": productive_meta["sector_code"].astype(str),
            "macrosector_code": productive_meta["macrosector_code"].astype(str),
            "node_label": productive_meta["full_label"].astype(str),
            "sam_node_id": productive_meta["node_id"].to_numpy(),
        }
    )

    # Full account table (every SAM account with classification + masks).
    account_nodes = meta[
        [
            "node_id",
            "region_code",
            "sector_code",
            "macrosector_code",
            "full_label",
            "account_class",
            "is_productive_account",
            "is_final_demand_account",
            "is_value_added_account",
            "is_external_input_account",
            "is_institutional_account",
        ]
    ].rename(columns={"node_id": "sam_node_id"})

    # ---- Blocks ----
    Z0 = build_productive_block(Z, productive_idx)
    FD0 = build_final_demand_vector(Z, productive_idx, final_demand_idx)
    VA0 = build_value_added_block(Z, value_added_idx, productive_idx)
    IMP0 = build_external_input_block(Z, external_input_idx, productive_idx)
    X0 = build_output_vector(Z0, FD0)

    globsec_of, sector_mapping = build_globsec_mapping(productive_meta)

    A0 = None
    if save_a0:
        denom = X0.copy()
        denom[denom == 0.0] = np.nan
        A0 = np.nan_to_num(Z0 / denom[None, :], nan=0.0)

    diagnostics = compute_accounting_diagnostics(Z0, VA0, X0, IMP0)

    # ---- Report ----
    report: Dict[str, Any] = {
        "sam_dir": str(sam_dir),
        "n_accounts_total": int(len(meta)),
        "n_productive": int(productive_idx.size),
        "n_final_demand": int(final_demand_idx.size),
        "n_value_added": int(value_added_idx.size),
        "n_external_input": int(external_input_idx.size),
        "n_sector_groups": int(sector_mapping.shape[0]),
        "Z0_shape": list(Z0.shape),
        "VA0_shape": list(VA0.shape),
        "IMP0_shape": list(IMP0.shape),
        "FD0_length": int(FD0.shape[0]),
        "X0_length": int(X0.shape[0]),
        "totals": {
            "total_Z0": float(Z0.sum()),
            "total_FD0": float(FD0.sum()),
            "total_VA0": float(VA0.sum()),
            "total_IMP0": float(IMP0.sum()),
            "total_X0": float(X0.sum()),
        },
        "row_vs_column_output": diagnostics,
        "account_class_counts": meta["account_class"].value_counts().to_dict(),
        "macrosector_counts": meta["macrosector_code"].value_counts().to_dict(),
        "node_ordering": "region_code ascending, then sector_code ascending",
        "matrix_orientation": "Z0[i, j] = value supplied by seller i to buyer j",
        "x0_definition": "X0 = row_sum(Z0) + FD0",
    }

    # ---- Warn loudly on a large accounting gap ----
    rel = diagnostics["max_rel_error"]
    if rel > 0.05:
        report["warning"] = (
            f"Row-vs-column output gap is large (max relative error {rel:.3%}). "
            "Row and column output are NOT forced equal; inspect the SAM."
        )

    paths = {}
    if write:
        paths = write_model_inputs(
            out_dir=out_dir,
            productive_nodes=productive_nodes,
            account_nodes=account_nodes,
            Z0=Z0,
            FD0=FD0,
            X0=X0,
            VA0=VA0,
            IMP0=IMP0,
            globsec_of=globsec_of,
            sector_mapping=sector_mapping,
            report=report,
            A0=A0,
        )
        report["outputs_written"] = paths

    return {
        "productive_nodes": productive_nodes,
        "account_nodes": account_nodes,
        "Z0": Z0,
        "FD0": FD0,
        "X0": X0,
        "VA0": VA0,
        "IMP0": IMP0,
        "A0": A0,
        "globsec_of": globsec_of,
        "sector_mapping": sector_mapping,
        "report": report,
        "paths": paths,
    }


def load_model_inputs(model_dir: Path) -> Dict[str, Any]:
    """Load previously written model inputs from ``model_dir``."""
    model_dir = Path(model_dir)
    productive_nodes = pd.read_csv(model_dir / "productive_nodes.csv")
    Z0 = np.load(model_dir / "Z0.npy")
    imp_path = model_dir / "IMP0.npy"
    return {
        "productive_nodes": productive_nodes,
        "Z0": Z0,
        "FD0": np.load(model_dir / "FD0.npy"),
        "X0": np.load(model_dir / "X0.npy"),
        "VA0": np.load(model_dir / "VA0.npy"),
        "IMP0": np.load(imp_path) if imp_path.exists() else np.zeros((0, Z0.shape[0])),
        "globsec_of": np.load(model_dir / "globsec_of.npy"),
        "sector_mapping": pd.read_csv(model_dir / "sector_mapping.csv"),
    }
