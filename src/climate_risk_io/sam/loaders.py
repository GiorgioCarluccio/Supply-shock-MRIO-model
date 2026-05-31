"""Runtime loaders for local SAM artifacts.

These functions only read local files and never connect to Databricks.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from config.paths import SAM_INTERIM_DIR, SAM_PROCESSED_DIR


def load_sam_dense_model(sam_dir: Path | None = None, mmap: bool = True) -> dict:
    """Load the dense SAM model artifacts.

    Returns a dict with ``nodes`` (DataFrame), ``Z`` (dense NumPy matrix),
    ``x`` (1-D NumPy vector aligned with ``nodes`` by ``node_id``) and
    ``report`` (dict). When ``mmap`` is True the matrix is memory-mapped so it
    does not have to fit in RAM.
    """
    if sam_dir is None:
        sam_dir = SAM_PROCESSED_DIR
    sam_dir = Path(sam_dir)

    nodes_path = sam_dir / "nodes.csv"
    z_path = sam_dir / "z_matrix.npy"
    x_path = sam_dir / "x_vector.npy"
    report_path = sam_dir / "sam_build_report.json"

    for path in [nodes_path, z_path, x_path, report_path]:
        if not path.exists():
            raise FileNotFoundError(f"Required SAM model artifact not found: {path}")

    with report_path.open("r", encoding="utf-8") as file:
        report = json.load(file)

    Z = np.load(z_path, mmap_mode="r") if mmap else np.load(z_path)

    return {
        "nodes": pd.read_csv(nodes_path),
        "Z": Z,
        "x": np.load(x_path),
        "report": report,
    }


def load_sam_flows_parquet(path: Path | None = None) -> pd.DataFrame:
    """DEPRECATED. Optional long-format extract reader from the old workflow.

    The dense matrix workflow does not require a full Parquet extract. Kept only
    for compatibility if an optional extract was retained.
    """
    if path is None:
        path = SAM_INTERIM_DIR / "sam_flows.parquet"
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"SAM flows parquet not found: {path}")
    return pd.read_parquet(path)


def load_sam_model_inputs(sam_dir: Path | None = None) -> dict:
    """DEPRECATED. Loader for the old sparse (.npz) workflow.

    Use :func:`load_sam_dense_model` instead.
    """
    from scipy import sparse

    if sam_dir is None:
        sam_dir = SAM_PROCESSED_DIR
    sam_dir = Path(sam_dir)

    nodes_path = sam_dir / "nodes.csv"
    z_path = sam_dir / "z_matrix_sparse.npz"
    x_path = sam_dir / "x_vector.parquet"
    province_mapping_path = sam_dir / "province_mapping.csv"
    sector_mapping_path = sam_dir / "sector_mapping.csv"
    report_path = sam_dir / "sam_build_report.json"

    for path in [
        nodes_path,
        z_path,
        x_path,
        province_mapping_path,
        sector_mapping_path,
        report_path,
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Required SAM model input not found: {path}")

    with report_path.open("r", encoding="utf-8") as file:
        report = json.load(file)

    return {
        "nodes": pd.read_csv(nodes_path),
        "Z": sparse.load_npz(z_path),
        "x": pd.read_parquet(x_path),
        "province_mapping": pd.read_csv(province_mapping_path),
        "sector_mapping": pd.read_csv(sector_mapping_path),
        "report": report,
    }
