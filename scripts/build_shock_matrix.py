"""Build the node-level shock matrix.

Joins the canonical hazard exposure table, the sector vulnerability table, the
scenario library, the productive node table and the province crosswalk into
``data/processed/shocks/shock_matrix.csv`` (one row per scenario x node).

Run from the project root::

    .\\.venv\\Scripts\\python.exe scripts\\build_shock_matrix.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from climate_risk_io.shocks import exposure_loader, scenario_library, sector_vulnerability
from climate_risk_io.shocks import shock_matrix as shock_matrix_mod
from config.paths import (
    HAZARD_EXPOSURE_PATH,
    MODEL_INPUTS_DIR,
    PROVINCE_CROSSWALK_PATH,
    SCENARIO_LIBRARY_PATH,
    SECTOR_VULNERABILITY_PATH,
    SHOCK_MATRIX_PATH,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exposure", default=str(HAZARD_EXPOSURE_PATH))
    parser.add_argument("--vulnerability", default=str(SECTOR_VULNERABILITY_PATH))
    parser.add_argument("--scenarios", default=str(SCENARIO_LIBRARY_PATH))
    parser.add_argument(
        "--productive-nodes",
        default=str(MODEL_INPUTS_DIR / "productive_nodes.csv"),
    )
    parser.add_argument("--crosswalk", default=str(PROVINCE_CROSSWALK_PATH))
    parser.add_argument("--out", default=str(SHOCK_MATRIX_PATH))
    parser.add_argument(
        "--all-scenarios",
        action="store_true",
        help="Include non-dashboard scenarios too (default: dashboard only).",
    )
    parser.add_argument(
        "--region-code-equals-province",
        action="store_true",
        help="Explicit opt-in: SAM region codes already equal ISTAT province codes.",
    )
    args = parser.parse_args()

    print("\n=== Build shock matrix ===")

    exposure = pd.read_csv(args.exposure)
    vulnerability = sector_vulnerability.load_sector_vulnerability(args.vulnerability)
    scenarios = scenario_library.load_scenario_library(args.scenarios)
    productive_nodes = pd.read_csv(args.productive_nodes)
    crosswalk = exposure_loader.load_crosswalk(Path(args.crosswalk))

    matrix = shock_matrix_mod.build_shock_matrix(
        exposure=exposure,
        vulnerability=vulnerability,
        scenarios=scenarios,
        productive_nodes=productive_nodes,
        crosswalk=crosswalk,
        dashboard_only=not args.all_scenarios,
        region_code_equals_province=args.region_code_equals_province,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    matrix.to_csv(out_path, index=False)

    print(f"\nWrote {len(matrix)} rows -> {out_path}")
    print("Supply shock by scenario (mean / max):")
    summary = matrix.groupby("scenario_id")["supply_shock"].agg(["mean", "max"])
    print(summary.to_string())
    print("\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
