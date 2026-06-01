"""Build the editable static scenario library.

Writes ``data/processed/shocks/scenario_library.csv`` with one row per dashboard
scenario (heatwave_central, flood_low/medium/high, landslide_p1..p4) and the
calibration knobs for each. Edit the CSV to tune base days, intensity, lambda
or caps.

Run from the project root::

    .\\.venv\\Scripts\\python.exe scripts\\build_scenario_library.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from climate_risk_io.shocks import scenario_library
from config.paths import SCENARIO_LIBRARY_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(SCENARIO_LIBRARY_PATH))
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing (possibly hand-edited) library.",
    )
    args = parser.parse_args()

    print("\n=== Build scenario library ===")
    out_path = Path(args.out)
    if out_path.exists() and not args.force:
        print(
            f"{out_path} already exists; keeping the edited library. "
            "Use --force to regenerate defaults."
        )
        return 0

    lib = scenario_library.build_scenario_library()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lib.to_csv(out_path, index=False)

    print(f"Wrote {len(lib)} scenarios -> {out_path}")
    print(lib[["scenario_id", "hazard", "severity", "base_interruption_days"]].to_string(index=False))
    print("\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
