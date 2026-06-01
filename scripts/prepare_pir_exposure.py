"""Parse the raw ISPRA PIR workbook into a clean province exposure table.

Reads ``data/raw/ispra/province_pir.xlsx`` and writes
``data/processed/climate/province_pir_clean.csv`` with flood / landslide
exposure expressed as shares in [0, 1].

Run from the project root::

    .\\.venv\\Scripts\\python.exe scripts\\prepare_pir_exposure.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from climate_risk_io.shocks import pir_parser
from config.paths import PROVINCE_PIR_CLEAN_PATH, PROVINCE_PIR_RAW_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", default=str(PROVINCE_PIR_RAW_PATH))
    parser.add_argument("--out", default=str(PROVINCE_PIR_CLEAN_PATH))
    args = parser.parse_args()

    print("\n=== Prepare ISPRA PIR exposure ===")
    print(f"Raw : {args.raw}")
    print(f"Out : {args.out}")

    clean = pir_parser.parse_pir_workbook(Path(args.raw))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(out_path, index=False)

    print(f"\nWrote {len(clean)} provinces.")
    print("Column unit summary (shares in [0, 1]):")
    print(json.dumps(pir_parser.summarise(clean), indent=2))
    print("\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
