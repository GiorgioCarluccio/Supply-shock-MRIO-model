r"""Static setup test for the dense SAM ingestion layer.

This test does NOT require a live Databricks connection. It verifies that the
SAM source files exist, that the SAM package modules import, that the column
mapping points at the correct table and columns (and excludes the right ones),
that the SAM scripts compile, and that ``config.paths`` exposes the SAM
processed directory.

Run from the project root:

    .\.venv\Scripts\python.exe test_sam_static_setup.py
"""

from __future__ import annotations

import importlib
import py_compile
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


EXPECTED_SAM_FILES = [
    "scripts/inspect_sam_databricks.py",
    "scripts/build_sam_dense_matrix_from_databricks.py",
    "scripts/test_sam_dense_matrix.py",
    "src/climate_risk_io/sam/__init__.py",
    "src/climate_risk_io/sam/databricks_client.py",
    "src/climate_risk_io/sam/mappings.py",
    "src/climate_risk_io/sam/loaders.py",
    "src/climate_risk_io/sam/validators.py",
    "src/climate_risk_io/sam/dense_builder.py",
]

# Scripts that import pyspark at module load are compiled but not imported here,
# because pyspark/Databricks Connect is not required for this static pass.
SCRIPTS_TO_COMPILE = [
    "scripts/inspect_sam_databricks.py",
    "scripts/build_sam_dense_matrix_from_databricks.py",
    "scripts/test_sam_dense_matrix.py",
]

# Modules safe to import without pyspark/scipy heavy deps.
SAM_PACKAGE_MODULES = [
    "climate_risk_io.sam",
    "climate_risk_io.sam.mappings",
    "climate_risk_io.sam.loaders",
    "climate_risk_io.sam.validators",
    "climate_risk_io.sam.dense_builder",
]

EXPECTED_TABLE = "ml.sam.mrsam_downscaled_y"

REQUIRED_MAPPING_KEYS = [
    "matrix_id",
    "origin_region",
    "origin_sector",
    "destination_region",
    "destination_sector",
    "flow_value",
    "time_period",
    "row_label",
    "col_label",
]

REQUIRED_EXCLUDED = [
    "share",
    "materialized_at",
    "mlflow_experiment_name",
    "mlflow_run_id",
]

REQUIRED_SAM_PATH_ATTRS = [
    "SAM_PROCESSED_DIR",
]


def print_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def check_files_exist() -> bool:
    print_header("Checking expected dense SAM files")
    ok = True
    for relative_path in EXPECTED_SAM_FILES:
        path = PROJECT_ROOT / relative_path
        exists = path.exists()
        print(f"{'OK' if exists else 'MISSING':8} {relative_path}")
        if not exists:
            ok = False
    return ok


def check_compilation() -> bool:
    print_header("Checking SAM scripts compile")
    ok = True
    for relative_path in SCRIPTS_TO_COMPILE:
        path = PROJECT_ROOT / relative_path
        if not path.exists():
            print(f"{'MISSING':8} {relative_path}")
            ok = False
            continue
        try:
            py_compile.compile(str(path), doraise=True)
            print(f"{'OK':8} {relative_path}")
        except py_compile.PyCompileError as exc:
            print(f"{'ERROR':8} {relative_path}")
            print(exc)
            ok = False
    return ok


def check_module_imports() -> bool:
    print_header("Checking SAM package modules import")
    ok = True
    for module_name in SAM_PACKAGE_MODULES:
        try:
            importlib.import_module(module_name)
            print(f"{'OK':8} {module_name}")
        except Exception as exc:  # noqa: BLE001
            print(f"{'ERROR':8} {module_name}: {exc}")
            ok = False
    return ok


def check_mapping() -> bool:
    print_header("Checking SAM table, column mapping and exclusions")
    try:
        from climate_risk_io.sam.mappings import (
            COLUMNS_EXCLUDED,
            SAM_COLUMN_CONFIG,
            SAM_TABLE,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR    Could not import mappings: {exc}")
        return False

    ok = True

    if SAM_TABLE == EXPECTED_TABLE:
        print(f"{'OK':8} SAM_TABLE == {EXPECTED_TABLE}")
    else:
        print(f"{'ERROR':8} SAM_TABLE is {SAM_TABLE!r}, expected {EXPECTED_TABLE!r}")
        ok = False

    for key in REQUIRED_MAPPING_KEYS:
        if key in SAM_COLUMN_CONFIG:
            print(f"{'OK':8} mapping key: {key} -> {SAM_COLUMN_CONFIG[key]}")
        else:
            print(f"{'MISSING':8} mapping key: {key}")
            ok = False

    # share / materialized_at must NOT be matrix-building columns.
    for forbidden in ["share", "materialized_at"]:
        if forbidden in SAM_COLUMN_CONFIG:
            print(f"{'ERROR':8} {forbidden} must not be in SAM_COLUMN_CONFIG")
            ok = False
        else:
            print(f"{'OK':8} {forbidden} excluded from SAM_COLUMN_CONFIG")

    for col in REQUIRED_EXCLUDED:
        if col in COLUMNS_EXCLUDED:
            print(f"{'OK':8} COLUMNS_EXCLUDED contains: {col}")
        else:
            print(f"{'MISSING':8} COLUMNS_EXCLUDED missing: {col}")
            ok = False

    return ok


def check_config_paths() -> bool:
    print_header("Checking config.paths SAM directory")
    try:
        import config.paths as paths
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR    Could not import config.paths: {exc}")
        return False

    ok = True
    for attr in REQUIRED_SAM_PATH_ATTRS:
        if hasattr(paths, attr):
            print(f"{'OK':8} {attr}: {getattr(paths, attr)}")
        else:
            print(f"{'MISSING':8} {attr}")
            ok = False
    return ok


def main() -> int:
    print_header("Supply-shock-MRIO-model dense SAM static setup test")

    checks = {
        "files_exist": check_files_exist(),
        "scripts_compile": check_compilation(),
        "modules_import": check_module_imports(),
        "mapping": check_mapping(),
        "config_paths": check_config_paths(),
    }

    print_header("Dense SAM static test summary")
    all_ok = True
    for check_name, passed in checks.items():
        print(f"{'PASSED' if passed else 'FAILED':8} {check_name}")
        if not passed:
            all_ok = False

    if all_ok:
        print("\nAll dense SAM static checks passed.")
        return 0

    print("\nSome dense SAM static checks failed. Review the messages above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
