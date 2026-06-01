"""Run the model for the static dashboard scenarios.

Reads the shock matrix and the model inputs, runs the reference IO propagation
model for each selected scenario, and writes per-scenario result tables under
``data/processed/simulations/<scenario_id>/``.

Run from the project root::

    .\\.venv\\Scripts\\python.exe scripts\\run_static_scenarios.py
    .\\.venv\\Scripts\\python.exe scripts\\run_static_scenarios.py --scenarios flood_high
    .\\.venv\\Scripts\\python.exe scripts\\run_static_scenarios.py --limit-scenarios 2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from climate_risk_io.model import input_builder
from climate_risk_io.shocks import batch_runner, scenario_library
from config.paths import (
    MODEL_INPUTS_DIR,
    SCENARIO_LIBRARY_PATH,
    SHOCK_MATRIX_PATH,
    SIMULATIONS_DIR,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shock-matrix", default=str(SHOCK_MATRIX_PATH))
    parser.add_argument("--scenarios-csv", default=str(SCENARIO_LIBRARY_PATH))
    parser.add_argument("--model-dir", default=str(MODEL_INPUTS_DIR))
    parser.add_argument("--out-dir", default=str(SIMULATIONS_DIR))
    parser.add_argument(
        "--scenarios",
        nargs="*",
        default=None,
        help="Specific scenario_id(s) to run (default: all dashboard scenarios).",
    )
    parser.add_argument("--limit-scenarios", type=int, default=None)
    parser.add_argument("--gamma", type=float, default=batch_runner.DEFAULT_GAMMA)
    parser.add_argument("--max-iter", type=int, default=batch_runner.DEFAULT_MAX_ITER)
    parser.add_argument("--tol", type=float, default=batch_runner.DEFAULT_TOL)
    parser.add_argument("--top-n", type=int, default=batch_runner.DEFAULT_TOP_N)
    args = parser.parse_args()

    print("\n=== Run static scenarios ===")
    shock_matrix = pd.read_csv(args.shock_matrix)
    scenarios = scenario_library.load_scenario_library(args.scenarios_csv)
    scenarios = scenarios[scenarios["is_dashboard_scenario"]].reset_index(drop=True)

    print("Loading model inputs ...")
    model_inputs = input_builder.load_model_inputs(Path(args.model_dir))
    print(f"Productive nodes: {len(model_inputs['productive_nodes'])}")

    summaries = batch_runner.run_scenarios(
        scenarios=scenarios,
        shock_matrix=shock_matrix,
        model_inputs=model_inputs,
        out_dir=Path(args.out_dir),
        scenario_ids=args.scenarios,
        limit_scenarios=args.limit_scenarios,
        gamma=args.gamma,
        max_iter=args.max_iter,
        tol=args.tol,
        top_n=args.top_n,
    )

    print("\n--- Summary ---")
    summary_df = pd.DataFrame(summaries)[
        ["scenario_id", "converged", "iterations", "total_direct_loss",
         "total_indirect_loss", "total_loss", "loss_rate_total"]
    ]
    print(summary_df.to_string(index=False))
    print(f"\nWrote {len(summaries)} scenario folders under {args.out_dir}")
    print("\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
