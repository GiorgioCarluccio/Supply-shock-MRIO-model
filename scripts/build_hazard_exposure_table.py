"""Build the canonical province hazard exposure table (and crosswalk).

Combines the validated heatwave indicators with the cleaned ISPRA flood /
landslide shares into ``data/processed/climate/province_hazard_exposure.csv``.

It also builds the NUTS-3 <-> ISTAT province crosswalk from the ISTAT provinces
layer and writes it to
``data/processed/mappings/province_code_crosswalk.csv`` (the shock-matrix step
requires this crosswalk).

Run from the project root::

    .\\.venv\\Scripts\\python.exe scripts\\build_hazard_exposure_table.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from climate_risk_io.shocks import exposure_loader, pir_parser
from config.paths import (
    HAZARD_EXPOSURE_PATH,
    HEATWAVE_INDICATORS_PATH,
    ISTAT_PROVINCES_GPKG_PATH,
    PROVINCE_CROSSWALK_PATH,
    PROVINCE_PIR_CLEAN_PATH,
    PROVINCE_PIR_RAW_PATH,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--heatwave", default=str(HEATWAVE_INDICATORS_PATH))
    parser.add_argument("--pir-clean", default=str(PROVINCE_PIR_CLEAN_PATH))
    parser.add_argument("--pir-raw", default=str(PROVINCE_PIR_RAW_PATH))
    parser.add_argument("--gpkg", default=str(ISTAT_PROVINCES_GPKG_PATH))
    parser.add_argument("--crosswalk-out", default=str(PROVINCE_CROSSWALK_PATH))
    parser.add_argument("--out", default=str(HAZARD_EXPOSURE_PATH))
    args = parser.parse_args()

    print("\n=== Build hazard exposure table ===")

    # 1) Province crosswalk (NUTS-3 <-> ISTAT).
    crosswalk = exposure_loader.build_province_crosswalk(Path(args.gpkg))
    crosswalk_path = Path(args.crosswalk_out)
    crosswalk_path.parent.mkdir(parents=True, exist_ok=True)
    crosswalk.to_csv(crosswalk_path, index=False)
    print(f"Crosswalk: {len(crosswalk)} provinces -> {crosswalk_path}")

    # 2) Cleaned PIR (parse on the fly if the clean file is missing).
    pir_clean_path = Path(args.pir_clean)
    if pir_clean_path.exists():
        import pandas as pd

        pir_clean = pd.read_csv(pir_clean_path)
    else:
        print("Clean PIR not found; parsing the raw workbook.")
        pir_clean = pir_parser.parse_pir_workbook(Path(args.pir_raw))
        pir_clean_path.parent.mkdir(parents=True, exist_ok=True)
        pir_clean.to_csv(pir_clean_path, index=False)

    # 3) Heatwave indicators.
    heatwave = exposure_loader.load_heatwave_indicators(Path(args.heatwave))

    # 4) Canonical exposure table.
    table = exposure_loader.build_hazard_exposure_table(heatwave, pir_clean, crosswalk)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out_path, index=False)

    print(f"\nWrote {len(table)} rows -> {out_path}")
    print("Rows per hazard/severity:")
    print(table.groupby(["hazard", "severity"]).size().to_string())
    print("\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
