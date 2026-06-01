"""Add the macrosector code to an existing dense SAM ``nodes.csv``.

The macrosector is the third ``__``-separated part of the source account labels
(``row_label`` / ``col_label``). Older dense-matrix builds dropped it, leaving a
two-part ``region__sector`` node table that cannot be classified into
productive / final-demand / value-added blocks.

This script recovers the macrosector locally **without** touching Databricks, by
reading the labels from the interim long-format SAM parquet, and rewrites
``nodes.csv`` in place:

* adds a ``macrosector_code`` column;
* upgrades ``node_label`` to the canonical ``region__sector__macrosector`` form;
* preserves the existing ``node_id`` order so it stays aligned with
  ``z_matrix.npy`` / ``x_vector.npy``.

New dense builds produced by ``build_sam_dense_matrix_from_databricks.py`` already
include the macrosector, so this script is only needed to upgrade an artifact
built before that fix.

Run from the project root::

    .\\.venv\\Scripts\\python.exe scripts\\enrich_sam_nodes_with_macrosector.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.paths import SAM_INTERIM_DIR, SAM_PROCESSED_DIR


def build_sector_macrosector_map(parquet_path: Path) -> dict:
    """Derive a sector_code -> macrosector_code map from the SAM label columns."""
    df = pd.read_parquet(
        parquet_path,
        columns=["origin_sector", "destination_sector", "row_label", "col_label"],
    )

    mapping: dict[str, set] = {}
    for sector_col, label_col in [
        ("origin_sector", "row_label"),
        ("destination_sector", "col_label"),
    ]:
        labels = df[label_col].astype(str).str.split("__", expand=True)
        if labels.shape[1] < 3:
            continue
        for sector, macro in zip(df[sector_col].astype(str), labels[2].astype(str)):
            mapping.setdefault(sector, set()).add(macro)

    conflicts = {s: m for s, m in mapping.items() if len(m) > 1}
    if conflicts:
        raise ValueError(f"Sector maps to multiple macrosectors: {conflicts}")

    return {sector: next(iter(macros)) for sector, macros in mapping.items()}


def main() -> int:
    nodes_path = SAM_PROCESSED_DIR / "nodes.csv"
    parquet_path = SAM_INTERIM_DIR / "sam_flows.parquet"

    if not nodes_path.exists():
        print(f"ERROR: {nodes_path} not found. Build the dense SAM matrix first.")
        return 1
    if not parquet_path.exists():
        print(
            f"ERROR: {parquet_path} not found. The macrosector can only be "
            "recovered from the source labels. Rebuild the SAM from Databricks "
            "with the macrosector-aware ingestion instead."
        )
        return 1

    nodes = pd.read_csv(nodes_path)
    print(f"Loaded {len(nodes)} nodes from {nodes_path}")

    sector_macro = build_sector_macrosector_map(parquet_path)
    print(f"Derived macrosector map for {len(sector_macro)} sector codes.")

    node_sectors = set(nodes["sector_code"].astype(str))
    missing = sorted(node_sectors - set(sector_macro))
    if missing:
        print(f"ERROR: no macrosector found for sectors: {missing}")
        return 1

    nodes["macrosector_code"] = nodes["sector_code"].astype(str).map(sector_macro)
    nodes["node_label"] = (
        nodes["region_code"].astype(str)
        + "__"
        + nodes["sector_code"].astype(str)
        + "__"
        + nodes["macrosector_code"].astype(str)
    )

    ordered_cols = ["node_id", "region_code", "sector_code", "macrosector_code", "node_label"]
    extra = [c for c in nodes.columns if c not in ordered_cols]
    nodes = nodes[ordered_cols + extra]
    nodes.to_csv(nodes_path, index=False)

    print(f"Rewrote {nodes_path} with macrosector_code and three-part node_label.")
    print("Macrosector counts:")
    print(nodes["macrosector_code"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
