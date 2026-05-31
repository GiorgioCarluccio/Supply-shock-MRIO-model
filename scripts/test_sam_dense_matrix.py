"""Validate the dense SAM matrix artifacts.

Run from the project root:

    .\\.venv\\Scripts\\python.exe scripts\\test_sam_dense_matrix.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from climate_risk_io.sam.validators import validate_dense_model_outputs
from config.paths import SAM_PROCESSED_DIR


REQUIRED_EXCLUDED = ["share", "materialized_at", "mlflow_experiment_name", "mlflow_run_id"]
EXPECTED_ORIENTATION = "rows = supplier/origin nodes; columns = buyer/destination nodes"


def main() -> None:
    print("\n=== Test Dense SAM Matrix ===")
    print(f"SAM directory: {SAM_PROCESSED_DIR}")
    print("Matrix convention: Z[i, j] = flow from supplier node i to buyer node j.")

    paths = {
        "nodes": SAM_PROCESSED_DIR / "nodes.csv",
        "Z": SAM_PROCESSED_DIR / "z_matrix.npy",
        "x": SAM_PROCESSED_DIR / "x_vector.npy",
        "report": SAM_PROCESSED_DIR / "sam_build_report.json",
    }

    failures = []
    for name, path in paths.items():
        if not path.exists():
            failures.append(f"{name} file is missing: {path}")
    if failures:
        print("\nFAIL")
        for failure in failures:
            print(f"- {failure}")
        sys.exit(1)

    try:
        nodes = pd.read_csv(paths["nodes"])
        Z = np.load(paths["Z"], mmap_mode="r")
        x = np.load(paths["x"])
        with paths["report"].open("r", encoding="utf-8") as file:
            report = json.load(file)
    except Exception as exc:
        print("\nFAIL")
        print(f"- Could not read dense SAM artifacts: {exc}")
        sys.exit(1)

    checks = []
    try:
        validate_dense_model_outputs(nodes, Z, x)
        checks.append("Core dense model-output validation passed.")
    except Exception as exc:
        failures.append(str(exc))

    if Z.ndim != 2 or Z.shape[0] != Z.shape[1]:
        failures.append(f"Z is not square: {Z.shape}")
    if Z.shape[0] != len(nodes):
        failures.append(f"Z dimension does not equal node count: {Z.shape}, {len(nodes)}")
    if len(x) != len(nodes):
        failures.append(f"x length does not equal node count: {len(x)}, {len(nodes)}")
    if not nodes["node_id"].is_unique:
        failures.append("node_id is not unique.")
    if nodes["node_id"].isna().any():
        failures.append("node_id contains null values.")

    z_sum = float(Z.sum())
    x_sum = float(x.sum())
    if not np.isclose(x_sum, z_sum, rtol=1e-9, atol=1e-6):
        failures.append(f"sum(x) {x_sum} does not equal Z.sum() {z_sum}.")

    orientation = report.get("orientation", "")
    if orientation != EXPECTED_ORIENTATION:
        failures.append(f"Report orientation is wrong: {orientation!r}")

    excluded = report.get("columns_excluded", [])
    missing_excluded = [c for c in REQUIRED_EXCLUDED if c not in excluded]
    if missing_excluded:
        failures.append(f"Report columns_excluded missing: {missing_excluded}")

    if failures:
        print("\nFAIL")
        for failure in failures:
            print(f"- {failure}")
        sys.exit(1)

    print("\nPASS")
    for check in checks:
        print(f"- {check}")
    print(f"- nodes.csv rows: {len(nodes):,}")
    print(f"- Z shape: {Z.shape}")
    print(f"- x_vector length: {len(x):,}")
    print(f"- Z.sum(): {z_sum}")
    print(f"- sum(x): {x_sum}")
    print(f"- Orientation: {orientation}")
    print(f"- columns_excluded: {excluded}")


if __name__ == "__main__":
    main()
