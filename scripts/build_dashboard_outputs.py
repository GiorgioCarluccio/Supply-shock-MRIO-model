"""Consolidate per-scenario simulation results into static dashboard files.

Reads ``data/processed/simulations/`` and writes frontend-ready files to
``data/processed/dashboard/``. No live model execution is required.

Run from the project root::

    .\\.venv\\Scripts\\python.exe scripts\\build_dashboard_outputs.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from climate_risk_io.shocks import dashboard_exports
from config.paths import DASHBOARD_DIR, SIMULATIONS_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulations-dir", default=str(SIMULATIONS_DIR))
    parser.add_argument("--dashboard-dir", default=str(DASHBOARD_DIR))
    args = parser.parse_args()

    print("\n=== Build dashboard outputs ===")
    written = dashboard_exports.build_dashboard_outputs(
        Path(args.simulations_dir), Path(args.dashboard_dir)
    )
    print(f"Wrote {len(written)} files:")
    for path in written:
        print(f"  {path}")
    print("\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
