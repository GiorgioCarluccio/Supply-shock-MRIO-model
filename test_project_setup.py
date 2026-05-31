from pathlib import Path
import importlib.util
import py_compile
import sys


PROJECT_ROOT = Path(__file__).resolve().parent


EXPECTED_PATHS = [
    "config/paths.py",
    "scripts/prepare_heatwave_inputs.py",
    "scripts/compute_heatwave_province_indicators.py",
    "scripts/plot_heatwave_cells_map.py",
    "scripts/test_heatwave_outputs.py",
    "src/climate_risk_io/__init__.py",
    "src/climate_risk_io/climate/__init__.py",
    "src/climate_risk_io/climate/heatwave.py",
    "src/climate_risk_io/io_utils/__init__.py",
    "src/climate_risk_io/io_utils/geospatial.py",
    "data/raw/eobs/tg_ens_mean_0.1deg_reg_v33.0e.nc",
    "data/raw/eobs/tx_ens_mean_0.1deg_reg_v33.0e.nc",
    "data/raw/istat/ProvCM01012024_g/ProvCM01012024_g_WGS84.shp",
    "data/raw/istat/ProvCM01012024_g/ProvCM01012024_g_WGS84.shx",
    "data/raw/istat/ProvCM01012024_g/ProvCM01012024_g_WGS84.dbf",
    "data/raw/istat/ProvCM01012024_g/ProvCM01012024_g_WGS84.prj",
    "data/raw/istat/ProvCM01012024_g/ProvCM01012024_g_WGS84.cpg",
    "data/processed/climate/eobs_tx_italy_1991_2025.nc",
    "data/processed/climate/istat_provinces_2024.gpkg",
    "data/processed/climate/province_heatwave_indicators.csv",
    "data/processed/climate/province_heatwave_indicators_yearly.csv",
]


PYTHON_FILES_TO_COMPILE = [
    "config/paths.py",
    "scripts/prepare_heatwave_inputs.py",
    "scripts/compute_heatwave_province_indicators.py",
    "scripts/plot_heatwave_cells_map.py",
    "scripts/test_heatwave_outputs.py",
    "src/climate_risk_io/climate/heatwave.py",
    "src/climate_risk_io/io_utils/geospatial.py",
]


def print_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def check_expected_paths() -> bool:
    print_header("Checking expected repository paths")

    ok = True

    for relative_path in EXPECTED_PATHS:
        path = PROJECT_ROOT / relative_path
        exists = path.exists()
        status = "OK" if exists else "MISSING"
        print(f"{status:8} {relative_path}")

        if not exists:
            ok = False

    return ok


def check_python_compilation() -> bool:
    print_header("Checking Python syntax")

    ok = True

    for relative_path in PYTHON_FILES_TO_COMPILE:
        path = PROJECT_ROOT / relative_path

        if not path.exists():
            print(f"SKIP     {relative_path} not found")
            ok = False
            continue

        try:
            py_compile.compile(str(path), doraise=True)
            print(f"OK       {relative_path}")
        except py_compile.PyCompileError as exc:
            print(f"ERROR    {relative_path}")
            print(exc)
            ok = False

    return ok


def check_config_paths_import() -> bool:
    print_header("Checking config.paths import")

    config_file = PROJECT_ROOT / "config" / "paths.py"

    if not config_file.exists():
        print("ERROR    config/paths.py not found")
        return False

    try:
        spec = importlib.util.spec_from_file_location("config.paths", config_file)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        required_attrs = [
            "PROJECT_ROOT",
            "DATA_DIR",
            "RAW_DATA_DIR",
            "INTERIM_DATA_DIR",
            "PROCESSED_DATA_DIR",
            "RAW_EOBS_DIR",
            "RAW_ISTAT_DIR",
            "RAW_ISPRA_DIR",
            "CLIMATE_PROCESSED_DIR",
            "CLIMATE_MAPS_DIR",
        ]

        ok = True

        for attr in required_attrs:
            if hasattr(module, attr):
                value = getattr(module, attr)
                print(f"OK       {attr}: {value}")
            else:
                print(f"MISSING  {attr}")
                ok = False

        return ok

    except Exception as exc:
        print("ERROR    Failed to import config.paths")
        print(exc)
        return False


def check_heatwave_outputs() -> bool:
    print_header("Checking heatwave output CSV files")

    try:
        import pandas as pd
    except ImportError:
        print("SKIP     pandas not installed")
        return False

    summary_path = PROJECT_ROOT / "data" / "processed" / "climate" / "province_heatwave_indicators.csv"
    yearly_path = PROJECT_ROOT / "data" / "processed" / "climate" / "province_heatwave_indicators_yearly.csv"

    if not summary_path.exists():
        print(f"ERROR    Missing {summary_path}")
        return False

    if not yearly_path.exists():
        print(f"ERROR    Missing {yearly_path}")
        return False

    summary = pd.read_csv(summary_path)
    yearly = pd.read_csv(yearly_path)

    ok = True

    required_summary_columns = [
        "province_code",
        "province_name",
        "province_abbr",
        "heatwave_exposure_raw",
        "heatwave_exposure_weight",
    ]

    required_yearly_columns = [
        "province_code",
        "province_name",
        "province_abbr",
        "year",
        "hot_days_mean",
        "hot_days_p75",
        "hot_days_p90",
        "hot_days_max",
        "n_grid_cells",
    ]

    print(f"Summary rows: {len(summary)}")
    print(f"Yearly rows:  {len(yearly)}")

    if len(summary) != 107:
        print("ERROR    Summary CSV should contain 107 provinces")
        ok = False
    else:
        print("OK       Summary CSV contains 107 provinces")

    unique_provinces = summary["province_code"].nunique()
    if unique_provinces != 107:
        print(f"ERROR    Expected 107 unique province_code values, got {unique_provinces}")
        ok = False
    else:
        print("OK       province_code has 107 unique values")

    missing_names = summary["province_name"].isna().sum()
    dash_names = (summary["province_name"] == "-").sum()

    if missing_names > 0 or dash_names > 0:
        print(f"ERROR    Invalid province names. Missing={missing_names}, dash={dash_names}")
        ok = False
    else:
        print("OK       No missing or '-' province names")

    for col in required_summary_columns:
        if col not in summary.columns:
            print(f"ERROR    Missing summary column: {col}")
            ok = False
        else:
            print(f"OK       Summary column found: {col}")

    for col in required_yearly_columns:
        if col not in yearly.columns:
            print(f"ERROR    Missing yearly column: {col}")
            ok = False
        else:
            print(f"OK       Yearly column found: {col}")

    if "heatwave_exposure_weight" in summary.columns:
        min_weight = summary["heatwave_exposure_weight"].min()
        max_weight = summary["heatwave_exposure_weight"].max()
        print(f"Exposure weight range: {min_weight:.4f} - {max_weight:.4f}")

        if min_weight < 0.10 or max_weight > 3.00:
            print("ERROR    Exposure weights outside expected 0.10 - 3.00 range")
            ok = False
        else:
            print("OK       Exposure weights inside expected range")

    if "year" in yearly.columns:
        min_year = yearly["year"].min()
        max_year = yearly["year"].max()
        print(f"Yearly indicator range: {min_year} - {max_year}")

        if min_year != 1991 or max_year != 2025:
            print("ERROR    Expected yearly indicators from 1991 to 2025")
            ok = False
        else:
            print("OK       Yearly indicators cover 1991-2025")

    return ok


def check_netcdf_metadata() -> bool:
    print_header("Checking NetCDF metadata")

    try:
        import xarray as xr
    except ImportError:
        print("SKIP     xarray not installed")
        return False

    nc_path = PROJECT_ROOT / "data" / "processed" / "climate" / "eobs_tx_italy_1991_2025.nc"

    if not nc_path.exists():
        print(f"ERROR    Missing {nc_path}")
        return False

    try:
        ds = xr.open_dataset(nc_path)
        print(ds)

        ok = True

        if "tx" not in ds.data_vars:
            print("ERROR    Variable 'tx' not found")
            ok = False
        else:
            print("OK       Variable 'tx' found")

        if "time" not in ds.dims or "latitude" not in ds.dims or "longitude" not in ds.dims:
            print("ERROR    Expected dimensions time, latitude, longitude")
            ok = False
        else:
            print("OK       Expected dimensions found")

        return ok

    except Exception as exc:
        print("ERROR    Failed to open NetCDF file")
        print(exc)
        return False


def check_gitignore() -> bool:
    print_header("Checking .gitignore")

    gitignore_path = PROJECT_ROOT / ".gitignore"

    if not gitignore_path.exists():
        print("ERROR    .gitignore not found")
        return False

    content = gitignore_path.read_text(encoding="utf-8")

    expected_patterns = [
        ".venv/",
        "*.nc",
        "data/raw/",
        "data/interim/",
        "data/processed/",
    ]

    ok = True

    for pattern in expected_patterns:
        if pattern in content:
            print(f"OK       Pattern found: {pattern}")
        else:
            print(f"WARNING  Pattern not found: {pattern}")
            ok = False

    return ok


def main() -> int:
    print_header("Supply-shock-MRIO-model repository test")

    checks = {
        "expected_paths": check_expected_paths(),
        "python_compilation": check_python_compilation(),
        "config_paths_import": check_config_paths_import(),
        "heatwave_outputs": check_heatwave_outputs(),
        "netcdf_metadata": check_netcdf_metadata(),
        "gitignore": check_gitignore(),
    }

    print_header("Test summary")

    all_ok = True

    for check_name, passed in checks.items():
        status = "PASSED" if passed else "FAILED"
        print(f"{status:8} {check_name}")

        if not passed:
            all_ok = False

    if all_ok:
        print("\nAll checks passed.")
        return 0

    print("\nSome checks failed. Review the messages above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())