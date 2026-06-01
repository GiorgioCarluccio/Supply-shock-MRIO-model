"""Non-Databricks tests for the shock calibration pipeline.

Validates the PIR Excel parser, the heatwave exposure availability, the
canonical exposure table, the scenario library, the sector vulnerability table,
and the shock-matrix dimensions / bounds. No Databricks connection is required.

It uses the real input data when present (heatwave indicators, ISPRA workbook,
ISTAT provinces layer, productive nodes) and a small synthetic fixture for the
pure calibration / shock-matrix logic so the core checks always run.

Run from the project root::

    .\\.venv\\Scripts\\python.exe scripts\\test_shock_pipeline.py
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from climate_risk_io.shocks import (
    calibration,
    exposure_loader,
    pir_parser,
    scenario_library,
    sector_vulnerability,
)
from climate_risk_io.shocks import shock_matrix as shock_matrix_mod
from config.paths import (
    HEATWAVE_INDICATORS_PATH,
    ISTAT_PROVINCES_GPKG_PATH,
    MODEL_INPUTS_DIR,
    PROVINCE_PIR_RAW_PATH,
)

_RESULTS = []


def check(name: str, fn) -> None:
    try:
        fn()
        _RESULTS.append((name, True, ""))
        print(f"  PASS  {name}")
    except Exception as exc:  # noqa: BLE001 - test harness reports all failures
        _RESULTS.append((name, False, str(exc)))
        print(f"  FAIL  {name}: {exc}")
        traceback.print_exc()


# --------------------------------------------------------------------------- #
# Synthetic fixtures (always available)
# --------------------------------------------------------------------------- #
def _synthetic_crosswalk() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "province_code": [1, 2],
            "province_name": ["Alpha", "Beta"],
            "province_abbr": ["AL", "BE"],
            "region_code": ["R1", "R2"],
        }
    )


def _synthetic_nodes() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "node_id": [0, 1, 2, 3],
            "region_code": ["R1", "R1", "R2", "R2"],
            "sector_code": ["A01", "C10", "A01", "C10"],
            "macrosector_code": ["A", "I", "A", "I"],
            "node_label": ["R1__A01__A", "R1__C10__I", "R2__A01__A", "R2__C10__I"],
        }
    )


def _synthetic_exposure(crosswalk: pd.DataFrame) -> pd.DataFrame:
    heatwave = pd.DataFrame(
        {
            "province_code": [1, 2],
            "heatwave_exposure_raw": [30.0, 10.0],
            "heatwave_exposure_weight": [2.0, 0.5],
        }
    )
    pir = pd.DataFrame(
        {
            "cod_prov": [1, 2],
            "imidp3_p": [0.2, 0.05],
            "imidp2_p": [0.5, 0.1],
            "imidp1_p": [0.8, 0.2],
            "imfrp4_p": [0.04, 0.0],
            "imfrp3_p": [0.08, 0.01],
            "imfrp2_p": [0.3, 0.02],
            "imfrp1_p": [0.4, 0.03],
        }
    )
    return exposure_loader.build_hazard_exposure_table(heatwave, pir, crosswalk)


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_calibration_formulas() -> None:
    # Flood uses raw share; heatwave uses the exposure weight.
    comp = calibration.exposure_component("flood", np.array([0.5]), np.array([2.0]))
    assert np.isclose(comp[0], 0.5), comp
    comp_hw = calibration.exposure_component(
        "heatwave", np.array([0.5]), np.array([2.0])
    )
    assert np.isclose(comp_hw[0], 2.0), comp_hw

    stop = calibration.equivalent_stop_days(0.5, 20, 0.8, 1.0)  # = 8 days
    assert np.isclose(stop, 8.0), stop
    sp = calibration.supply_shock(8.0, 0.25, working_days=250)  # 8/250 = 0.032
    assert np.isclose(sp, 0.032), sp
    sp_capped = calibration.supply_shock(100.0, 0.25, working_days=250)
    assert np.isclose(sp_capped, 0.25), sp_capped
    sd = calibration.demand_shock(0.032, 0.25, 0.10)
    assert np.isclose(sd, 0.008), sd
    # lambda * supply = 0.5 * 0.25 = 0.125, capped at 0.10.
    sd_capped = calibration.demand_shock(0.25, 0.5, 0.10)
    assert np.isclose(sd_capped, 0.10), sd_capped


def test_scenario_library() -> None:
    lib = scenario_library.build_scenario_library()
    assert len(lib) == 8, len(lib)
    assert lib["is_dashboard_scenario"].all()
    assert set(lib["hazard"]) == {"heatwave", "flood", "landslide"}
    # Lambda and caps are present and sane.
    assert (lib["max_supply_shock"] <= 1).all()
    assert (lib["demand_pass_through_lambda"] > 0).all()


def test_sector_vulnerability() -> None:
    nodes = _synthetic_nodes()
    table = sector_vulnerability.build_sector_vulnerability_table(nodes)
    # 2 sectors x 3 hazards.
    assert len(table) == 6, len(table)
    assert set(table["hazard"]) == {"heatwave", "flood", "landslide"}
    assert (table["sector_vulnerability"] > 0).all()


def test_exposure_table_synthetic() -> None:
    crosswalk = _synthetic_crosswalk()
    exposure = _synthetic_exposure(crosswalk)
    # 2 provinces x (1 heatwave + 3 flood + 4 landslide) = 16 rows.
    assert len(exposure) == 16, len(exposure)
    assert set(exposure["hazard"]) == {"heatwave", "flood", "landslide"}
    assert not exposure["raw_exposure"].isna().any()


def test_shock_matrix_synthetic() -> None:
    crosswalk = _synthetic_crosswalk()
    nodes = _synthetic_nodes()
    exposure = _synthetic_exposure(crosswalk)
    vuln = sector_vulnerability.build_sector_vulnerability_table(nodes)
    lib = scenario_library.build_scenario_library()

    matrix = shock_matrix_mod.build_shock_matrix(
        exposure=exposure,
        vulnerability=vuln,
        scenarios=lib,
        productive_nodes=nodes,
        crosswalk=crosswalk,
    )
    n_scenarios = len(lib)
    n_nodes = len(nodes)
    # Dimensions: every node receives one shock per scenario.
    assert len(matrix) == n_scenarios * n_nodes, len(matrix)
    per_scenario = matrix.groupby("scenario_id")["node_id"].nunique()
    assert (per_scenario == n_nodes).all()
    # No nulls.
    assert not matrix["supply_shock"].isna().any()
    assert not matrix["demand_shock"].isna().any()
    # Bounds.
    assert (matrix["supply_shock"] <= matrix["max_supply_shock"] + 1e-9).all()
    assert (matrix["demand_shock"] <= matrix["max_demand_shock"] + 1e-9).all()
    assert (matrix["supply_shock"] >= 0).all()
    assert (matrix["demand_shock"] >= 0).all()
    # Demand <= supply (lambda <= 1) before caps.
    assert (matrix["demand_shock"] <= matrix["supply_shock"] + 1e-9).all()


def test_shock_matrix_missing_region_fails() -> None:
    crosswalk = _synthetic_crosswalk()
    nodes = _synthetic_nodes()
    nodes.loc[0, "region_code"] = "R_UNKNOWN"
    exposure = _synthetic_exposure(crosswalk)
    vuln = sector_vulnerability.build_sector_vulnerability_table(_synthetic_nodes())
    lib = scenario_library.build_scenario_library()
    try:
        shock_matrix_mod.build_shock_matrix(
            exposure=exposure,
            vulnerability=vuln,
            scenarios=lib,
            productive_nodes=nodes,
            crosswalk=crosswalk,
        )
    except ValueError:
        return
    raise AssertionError("Expected a ValueError for an unmapped region code.")


def test_pir_parser_real() -> None:
    if not Path(PROVINCE_PIR_RAW_PATH).exists():
        print("    (skip) raw ISPRA workbook not present")
        return
    clean = pir_parser.parse_pir_workbook(Path(PROVINCE_PIR_RAW_PATH))
    assert len(clean) == pir_parser.EXPECTED_PROVINCES, len(clean)
    assert not clean["cod_prov"].isna().any()
    for col in pir_parser.HAZARD_COLUMNS:
        assert (clean[col] >= 0).all() and (clean[col] <= 1).all(), col


def test_heatwave_available_real() -> None:
    if not Path(HEATWAVE_INDICATORS_PATH).exists():
        print("    (skip) heatwave indicators not present")
        return
    hw = exposure_loader.load_heatwave_indicators(Path(HEATWAVE_INDICATORS_PATH))
    assert "heatwave_exposure_weight" in hw.columns
    assert len(hw) > 0


def test_crosswalk_real() -> None:
    if not Path(ISTAT_PROVINCES_GPKG_PATH).exists():
        print("    (skip) ISTAT provinces layer not present")
        return
    crosswalk = exposure_loader.build_province_crosswalk(Path(ISTAT_PROVINCES_GPKG_PATH))
    assert len(crosswalk) == len(exposure_loader.NUTS_TO_SIGLA)
    assert not crosswalk["province_code"].duplicated().any()
    # Every productive-node region must be covered by the crosswalk.
    nodes_path = Path(MODEL_INPUTS_DIR) / "productive_nodes.csv"
    if nodes_path.exists():
        nodes = pd.read_csv(nodes_path)
        unmapped = set(nodes["region_code"].astype(str)) - set(
            crosswalk["region_code"].astype(str)
        )
        assert not unmapped, f"Unmapped node regions: {sorted(unmapped)}"


def test_full_pipeline_real() -> None:
    """End-to-end shock-matrix build on the real data (no model run)."""
    nodes_path = Path(MODEL_INPUTS_DIR) / "productive_nodes.csv"
    if not (
        Path(ISTAT_PROVINCES_GPKG_PATH).exists()
        and Path(HEATWAVE_INDICATORS_PATH).exists()
        and Path(PROVINCE_PIR_RAW_PATH).exists()
        and nodes_path.exists()
    ):
        print("    (skip) real inputs incomplete")
        return
    crosswalk = exposure_loader.build_province_crosswalk(Path(ISTAT_PROVINCES_GPKG_PATH))
    heatwave = exposure_loader.load_heatwave_indicators(Path(HEATWAVE_INDICATORS_PATH))
    pir = pir_parser.parse_pir_workbook(Path(PROVINCE_PIR_RAW_PATH))
    exposure = exposure_loader.build_hazard_exposure_table(heatwave, pir, crosswalk)
    nodes = pd.read_csv(nodes_path)
    vuln = sector_vulnerability.build_sector_vulnerability_table(nodes)
    lib = scenario_library.build_scenario_library()

    matrix = shock_matrix_mod.build_shock_matrix(
        exposure=exposure,
        vulnerability=vuln,
        scenarios=lib,
        productive_nodes=nodes,
        crosswalk=crosswalk,
    )
    assert len(matrix) == len(lib) * len(nodes), len(matrix)
    # Every node covered per scenario; no null shocks.
    per_scenario = matrix.groupby("scenario_id")["node_id"].nunique()
    assert (per_scenario == len(nodes)).all()
    assert not matrix["supply_shock"].isna().any()
    assert not matrix["demand_shock"].isna().any()
    assert (matrix["supply_shock"] <= matrix["max_supply_shock"] + 1e-9).all()
    assert (matrix["demand_shock"] <= matrix["max_demand_shock"] + 1e-9).all()


def main() -> int:
    print("\n=== Shock pipeline tests ===")
    print("\n[synthetic / unit]")
    check("calibration_formulas", test_calibration_formulas)
    check("scenario_library", test_scenario_library)
    check("sector_vulnerability", test_sector_vulnerability)
    check("exposure_table_synthetic", test_exposure_table_synthetic)
    check("shock_matrix_synthetic", test_shock_matrix_synthetic)
    check("shock_matrix_missing_region_fails", test_shock_matrix_missing_region_fails)

    print("\n[real data, if present]")
    check("pir_parser_real", test_pir_parser_real)
    check("heatwave_available_real", test_heatwave_available_real)
    check("crosswalk_real", test_crosswalk_real)
    check("full_pipeline_real", test_full_pipeline_real)

    n_pass = sum(1 for _, ok, _ in _RESULTS if ok)
    n_fail = len(_RESULTS) - n_pass
    print(f"\n=== {n_pass} passed, {n_fail} failed ===")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
