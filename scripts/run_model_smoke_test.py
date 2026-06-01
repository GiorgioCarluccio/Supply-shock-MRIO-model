"""Smoke-test the propagation model on the real SAM-derived inputs.

Loads the model-ready inputs, applies a small artificial supply shock, runs the
model and prints convergence status, the direct / indirect / total loss totals
and the top penalised / favoured flows.

By default the run is restricted to the productive nodes of the first few
regions, because the full productive block (thousands of nodes) requires a dense
LU factorisation that is heavy for a quick check. Use ``--full`` to run on the
entire productive block.

Run from the project root::

    .\\.venv\\Scripts\\python.exe scripts\\run_model_smoke_test.py
    .\\.venv\\Scripts\\python.exe scripts\\run_model_smoke_test.py --full
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from climate_risk_io.model import input_builder, results
from climate_risk_io.model.io_model import IOClimateModel
from config.paths import MODEL_INPUTS_DIR


def subset_inputs(inputs: dict, n_regions: int) -> dict:
    """Restrict the productive block to the first ``n_regions`` regions.

    The subset is rebuilt as a self-consistent closed mini-economy: dropping
    the other regions removes their inter-regional trade from ``Z0``, so the
    subset output vector is recomputed as ``X0 = row_sum(Z0) + FD0`` rather than
    reusing the full-economy ``X0`` (which still counts sales to dropped
    regions). This preserves the Leontief accounting identity, so a zero shock
    yields zero loss on the subset.
    """
    nodes = inputs["productive_nodes"]
    regions = sorted(nodes["region_code"].unique())[:n_regions]
    keep = nodes["region_code"].isin(regions).to_numpy()
    idx = np.where(keep)[0]

    sub_nodes = nodes.iloc[idx].reset_index(drop=True)
    sub_nodes["node_id"] = np.arange(len(sub_nodes), dtype=np.int64)

    Z0 = inputs["Z0"][np.ix_(idx, idx)]
    FD0 = inputs["FD0"][idx]
    X0 = Z0.sum(axis=1) + FD0  # closed mini-economy output

    # Remap sector-group ids to a contiguous 0-based range for the subset.
    old_groups = inputs["globsec_of"][idx]
    unique = sorted(np.unique(old_groups))
    remap = {g: i for i, g in enumerate(unique)}
    globsec_of = np.array([remap[g] for g in old_groups], dtype=np.int64)

    return {
        "productive_nodes": sub_nodes,
        "Z0": Z0,
        "FD0": FD0,
        "X0": X0,
        "globsec_of": globsec_of,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", default=str(MODEL_INPUTS_DIR))
    parser.add_argument("--full", action="store_true", help="Run on the full block.")
    parser.add_argument("--n-regions", type=int, default=3)
    parser.add_argument("--shock", type=float, default=0.30, help="Supply shock size.")
    parser.add_argument("--gamma", type=float, default=0.5)
    parser.add_argument("--max-iter", type=int, default=50)
    parser.add_argument("--tol", type=float, default=1e-6)
    args = parser.parse_args()

    print("\n=== Model Smoke Test ===")
    inputs = input_builder.load_model_inputs(Path(args.model_dir))

    if not args.full:
        inputs = subset_inputs(inputs, args.n_regions)
        print(f"Subset to first {args.n_regions} regions.")

    nodes = inputs["productive_nodes"]
    n = len(nodes)
    print(f"Productive nodes in run: {n}")

    model = IOClimateModel(
        Z0=inputs["Z0"],
        FD0=inputs["FD0"],
        X0=inputs["X0"],
        sector_group_of=inputs["globsec_of"],
        node_labels=nodes["node_label"].tolist(),
    )

    # Artificial supply shock on the first 5 nodes; no demand shock.
    sp = np.zeros(n, dtype=float)
    sp[: min(5, n)] = args.shock
    sd = np.zeros(n, dtype=float)

    print(f"Applying supply shock of {args.shock:.0%} to {min(5, n)} nodes...")
    run_output = model.run(
        sd=sd,
        sp=sp,
        gamma=args.gamma,
        max_iter=args.max_iter,
        tol=args.tol,
    )

    res = results.summarize_run(run_output, inputs["Z0"], inputs["X0"], nodes, top_n=10)

    print("\n--- Convergence ---")
    print(f"converged : {res.convergence_status}")
    print(f"iterations: {res.iterations}")
    print(f"demand gap: {run_output['demand_update_gap_last']:.6e}")
    print(f"variant   : {run_output['model_variant']}")

    print("\n--- Loss totals ---")
    print(f"direct_loss   : {res.totals['total_direct_loss']:.4f}")
    print(f"indirect_loss : {res.totals['total_indirect_loss']:.4f}")
    print(f"total_loss    : {res.totals['total_loss']:.4f}")
    if res.totals["total_direct_loss"] > 0:
        multiplier = res.totals["total_loss"] / res.totals["total_direct_loss"]
        print(f"total/direct  : {multiplier:.4f}")
    print(f"x_pre total   : {res.totals['total_x_pre']:.4f}")
    print(f"x_post total  : {res.totals['total_x_post']:.4f}")

    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 20)

    print("\n--- Top penalised flows ---")
    print(res.top_penalized_flows.to_string(index=False))
    print("\n--- Top favoured flows ---")
    print(res.top_favored_flows.to_string(index=False))

    print("\n=== Smoke test complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
