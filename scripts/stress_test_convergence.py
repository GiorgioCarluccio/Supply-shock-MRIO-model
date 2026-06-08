"""Stress-test the reference IO propagation model's convergence behaviour.

Runs one or more dashboard scenarios with full per-iteration history and reports
the demand-update-gap trajectory and the loss trajectory, so we can characterise
*why* the strict-min reference model fails to reach ``tol`` within ``max_iter``
(slow monotone plateau vs oscillation vs blow-up) and how the indirect/direct
loss split evolves.

Run from the project root::

    .\\.venv\\Scripts\\python.exe scripts\\stress_test_convergence.py
    .\\.venv\\Scripts\\python.exe scripts\\stress_test_convergence.py --scenarios heatwave_central flood_medium --max-iter 200
    .\\.venv\\Scripts\\python.exe scripts\\stress_test_convergence.py --gamma 0.5 --tol 1e-6
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

from climate_risk_io.model import input_builder
from climate_risk_io.model.io_model import IOClimateModel
from climate_risk_io.shocks import batch_runner, scenario_library
from config.paths import MODEL_INPUTS_DIR, SCENARIO_LIBRARY_PATH, SHOCK_MATRIX_PATH


def _fmt(x: float) -> str:
    return f"{x:,.2f}"


def run_one(scenario_id, shock_matrix, model_inputs, *, gamma, max_iter, tol):
    nodes = model_inputs["productive_nodes"]
    n = len(nodes)
    X0 = model_inputs["X0"]
    X0_sum = float(X0.sum())

    sm = shock_matrix[shock_matrix["scenario_id"] == scenario_id]
    if sm.empty:
        print(f"  !! no shock-matrix rows for scenario {scenario_id}")
        return None
    vectors = batch_runner.build_shock_vectors(sm, n)
    sp, sd = vectors["sp"], vectors["sd"]

    model = IOClimateModel(
        Z0=model_inputs["Z0"],
        FD0=model_inputs["FD0"],
        X0=X0,
        sector_group_of=model_inputs["globsec_of"],
        node_labels=nodes["node_label"].tolist() if "node_label" in nodes.columns else None,
    )
    out = model.run(sd=sd, sp=sp, gamma=gamma, max_iter=max_iter, tol=tol, return_history=True)

    gaps = out["demand_update_gap_history"]
    xhist = out["X_supply_history"]
    # Direct-loss reference: loss at the directly supply-shocked nodes only,
    # using the fixed capacity cap (independent of iteration).
    direct_cap_loss = float(np.sum(np.maximum(X0 - X0 * (1.0 - sp), 0.0)))

    print(f"\n=== {scenario_id} ===")
    print(f"  nodes shocked (sp>0): {int((sp > 0).sum())} / {n}   "
          f"max sp={sp.max():.4f}  mean sp={sp.mean():.6f}")
    print(f"  baseline output X0.sum() = {_fmt(X0_sum)}")
    print(f"  direct (capacity) loss   = {_fmt(direct_cap_loss)}  "
          f"({direct_cap_loss / X0_sum:.4%} of output)")
    print(f"  converged={out['converged']}  iterations={out['iterations']}  "
          f"final gap={out['demand_update_gap_last']:.3e}  tol={tol:.1e}")
    print("\n  iter |   demand_update_gap |    total_loss |  loss_rate |  indirect/direct")
    print("  -----+---------------------+---------------+------------+-----------------")
    milestones = set()
    nit = len(gaps)
    # show first 5, then a geometric-ish sampling, then last 3
    show = set(range(min(5, nit))) | {nit - 1, nit - 2, nit - 3}
    k = 5
    while k < nit:
        show.add(k)
        k = int(k * 1.6) + 1
    for i in sorted(x for x in show if 0 <= x < nit):
        x_sup_sum = float(xhist[i].sum())
        total_loss = X0_sum - x_sup_sum
        loss_rate = total_loss / X0_sum
        ratio = (total_loss - direct_cap_loss) / direct_cap_loss if direct_cap_loss > 0 else float("nan")
        print(f"  {i + 1:4d} | {gaps[i]:19.3e} | {total_loss:13,.1f} | {loss_rate:9.4%} | {ratio:15.2f}")
    return {
        "scenario_id": scenario_id,
        "converged": out["converged"],
        "iterations": out["iterations"],
        "final_gap": out["demand_update_gap_last"],
        "direct_cap_loss": direct_cap_loss,
        "final_total_loss": X0_sum - float(xhist[-1].sum()),
        "gaps": gaps,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scenarios", nargs="*", default=None,
                   help="scenario_id(s) to test (default: all dashboard scenarios)")
    p.add_argument("--gamma", type=float, default=0.5)
    p.add_argument("--max-iter", type=int, default=50)
    p.add_argument("--tol", type=float, default=1e-6)
    args = p.parse_args()

    print("=== Convergence stress test ===")
    print(f"gamma={args.gamma}  max_iter={args.max_iter}  tol={args.tol:.1e}")

    shock_matrix = pd.read_csv(SHOCK_MATRIX_PATH)
    model_inputs = input_builder.load_model_inputs(MODEL_INPUTS_DIR)

    scen = scenario_library.load_scenario_library(SCENARIO_LIBRARY_PATH)
    scen = scen[scen["is_dashboard_scenario"]]
    ids = args.scenarios or scen["scenario_id"].tolist()

    rows = []
    for sid in ids:
        r = run_one(sid, shock_matrix, model_inputs,
                    gamma=args.gamma, max_iter=args.max_iter, tol=args.tol)
        if r:
            rows.append(r)

    print("\n=== Summary ===")
    print(f"{'scenario':<18}{'conv':>6}{'iters':>7}{'final_gap':>13}"
          f"{'direct_loss':>15}{'total_loss':>15}{'tot/direct':>12}")
    for r in rows:
        ratio = r["final_total_loss"] / r["direct_cap_loss"] if r["direct_cap_loss"] > 0 else float("nan")
        print(f"{r['scenario_id']:<18}{str(r['converged']):>6}{r['iterations']:>7}"
              f"{r['final_gap']:>13.2e}{r['direct_cap_loss']:>15,.0f}"
              f"{r['final_total_loss']:>15,.0f}{ratio:>12.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
