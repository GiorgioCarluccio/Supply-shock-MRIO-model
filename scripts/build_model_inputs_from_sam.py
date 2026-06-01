"""Build model-ready inputs from the dense SAM artifact.

Reads ``data/processed/sam/`` (nodes.csv, z_matrix.npy, x_vector.npy), classifies
accounts from their macrosector, slices the productive block, and writes the
model-ready arrays and tables to ``data/processed/model_inputs/`` together with
``model_input_report.json``.

Run from the project root::

    .\\.venv\\Scripts\\python.exe scripts\\build_model_inputs_from_sam.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from climate_risk_io.model import input_builder
from config.paths import MODEL_INPUTS_DIR, SAM_PROCESSED_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sam-dir", default=str(SAM_PROCESSED_DIR))
    parser.add_argument("--out-dir", default=str(MODEL_INPUTS_DIR))
    parser.add_argument(
        "--save-a0",
        action="store_true",
        help="Also save the technical-coefficient matrix A0.npy (optional).",
    )
    parser.add_argument(
        "--mmap",
        action="store_true",
        help="Memory-map the dense SAM matrix instead of loading it into RAM.",
    )
    args = parser.parse_args()

    print("\n=== Build Model Inputs From SAM ===")
    print(f"SAM dir : {args.sam_dir}")
    print(f"Out dir : {args.out_dir}")

    result = input_builder.build_model_inputs(
        sam_dir=Path(args.sam_dir),
        out_dir=Path(args.out_dir),
        write=True,
        save_a0=args.save_a0,
        mmap=args.mmap,
    )

    report = result["report"]
    print("\n--- Report ---")
    print(json.dumps(report, indent=2))

    if "warning" in report:
        print("\nWARNING:", report["warning"])

    print("\n=== Done ===")
    print(f"Productive nodes : {report['n_productive']}")
    print(f"Final-demand cols: {report['n_final_demand']}")
    print(f"Value-added rows : {report['n_value_added']}")
    print(f"External rows    : {report['n_external_input']}")
    print(f"Z0 shape         : {report['Z0_shape']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
