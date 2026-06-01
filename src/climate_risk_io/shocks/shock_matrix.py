"""Assemble the node-level shock matrix.

The shock matrix has one row per ``scenario x productive node``. It joins:

* the canonical hazard exposure table (province x hazard x severity);
* the sector vulnerability table (sector x hazard);
* the scenario library (hazard x severity calibration knobs);
* the productive node table (node x region x sector);
* the province crosswalk (region_code <-> province_code).

It then applies the :mod:`calibration` formulas to produce per-node supply and
demand shocks, and validates that every productive node receives exactly one
shock per scenario, with no nulls and within the configured caps.
"""

from __future__ import annotations

import pandas as pd

from . import WORKING_DAYS
from . import calibration

SHOCK_METHOD = "equivalent_stop_days_v1"

# Column order of the output shock matrix.
SHOCK_MATRIX_COLUMNS = [
    "scenario_id",
    "hazard",
    "severity",
    "province_code",
    "region_code",
    "province_name",
    "province_abbr",
    "sector_code",
    "macrosector_code",
    "node_id",
    "raw_exposure",
    "exposure_weight",
    "sector_vulnerability",
    "base_interruption_days",
    "scenario_intensity_multiplier",
    "equivalent_stop_days",
    "working_days",
    "supply_shock",
    "demand_pass_through_lambda",
    "demand_shock",
    "max_supply_shock",
    "max_demand_shock",
    "shock_method",
]


def build_shock_matrix(
    exposure: pd.DataFrame,
    vulnerability: pd.DataFrame,
    scenarios: pd.DataFrame,
    productive_nodes: pd.DataFrame,
    crosswalk: pd.DataFrame,
    *,
    working_days: int = WORKING_DAYS,
    dashboard_only: bool = True,
    region_code_equals_province: bool = False,
) -> pd.DataFrame:
    """Build the node-level shock matrix for the selected scenarios.

    Parameters
    ----------
    dashboard_only:
        Restrict to scenarios flagged ``is_dashboard_scenario``.
    region_code_equals_province:
        Explicit opt-in for the case where SAM region codes already equal ISTAT
        province codes (then no crosswalk join is needed). Defaults to False so
        the identifier systems are never silently assumed equal.
    """
    scenarios = scenarios.copy()
    if dashboard_only:
        scenarios = scenarios[scenarios["is_dashboard_scenario"]].reset_index(drop=True)
    if scenarios.empty:
        raise ValueError("No scenarios selected to build the shock matrix.")

    nodes = _attach_province_code(productive_nodes, crosswalk, region_code_equals_province)

    frames = []
    for _, scenario in scenarios.iterrows():
        frames.append(_build_one_scenario(scenario, exposure, vulnerability, nodes, working_days))

    matrix = pd.concat(frames, ignore_index=True)
    matrix = matrix[SHOCK_MATRIX_COLUMNS]
    _validate(matrix, scenarios, nodes)
    return matrix


def _attach_province_code(
    productive_nodes: pd.DataFrame,
    crosswalk: pd.DataFrame,
    region_code_equals_province: bool,
) -> pd.DataFrame:
    nodes = productive_nodes.copy()
    nodes["region_code"] = nodes["region_code"].astype(str)

    if region_code_equals_province:
        nodes["province_code"] = pd.to_numeric(nodes["region_code"], errors="coerce")
        if nodes["province_code"].isna().any():
            raise ValueError(
                "region_code_equals_province=True but some region_code values are "
                "not numeric ISTAT province codes."
            )
        nodes["province_code"] = nodes["province_code"].astype(int)
        # province_name / province_abbr are unknown in this mode.
        nodes["province_name"] = nodes["region_code"]
        nodes["province_abbr"] = nodes["region_code"]
        return nodes

    merged = nodes.merge(
        crosswalk[["region_code", "province_code", "province_name", "province_abbr"]],
        on="region_code",
        how="left",
    )
    unmapped = merged[merged["province_code"].isna()]["region_code"].unique()
    if len(unmapped) > 0:
        raise ValueError(
            "The following productive-node region codes are missing from the "
            f"province crosswalk: {sorted(unmapped)}. Update "
            "data/processed/mappings/province_code_crosswalk.csv."
        )
    merged["province_code"] = merged["province_code"].astype(int)
    return merged


def _build_one_scenario(
    scenario: pd.Series,
    exposure: pd.DataFrame,
    vulnerability: pd.DataFrame,
    nodes: pd.DataFrame,
    working_days: int,
) -> pd.DataFrame:
    hazard = str(scenario["hazard"])
    severity = str(scenario["severity"])

    exp = exposure[
        (exposure["hazard"] == hazard) & (exposure["severity"] == severity)
    ]
    if exp.empty:
        raise ValueError(
            f"No exposure rows for hazard='{hazard}', severity='{severity}' "
            f"(scenario '{scenario['scenario_id']}')."
        )
    exp = exp[["province_code", "raw_exposure", "exposure_weight"]]

    vuln = vulnerability[vulnerability["hazard"] == hazard][
        ["sector_code", "sector_vulnerability"]
    ]
    if vuln.empty:
        raise ValueError(f"No sector vulnerability rows for hazard='{hazard}'.")

    df = nodes.merge(exp, on="province_code", how="left")
    df = df.merge(vuln, on="sector_code", how="left")

    missing_exp = df["raw_exposure"].isna()
    if missing_exp.any():
        bad = df.loc[missing_exp, "province_code"].unique()
        raise ValueError(
            f"Scenario '{scenario['scenario_id']}': no exposure for province "
            f"codes {sorted(bad)}."
        )
    missing_vuln = df["sector_vulnerability"].isna()
    if missing_vuln.any():
        bad = df.loc[missing_vuln, "sector_code"].unique()
        raise ValueError(
            f"Scenario '{scenario['scenario_id']}': no vulnerability for sectors "
            f"{sorted(bad)} under hazard '{hazard}'."
        )

    base_days = float(scenario["base_interruption_days"])
    multiplier = float(scenario["scenario_intensity_multiplier"])
    lam = float(scenario["demand_pass_through_lambda"])
    max_sp = float(scenario["max_supply_shock"])
    max_sd = float(scenario["max_demand_shock"])

    exp_component = calibration.exposure_component(
        hazard, df["raw_exposure"].to_numpy(), df["exposure_weight"].to_numpy()
    )
    stop_days = calibration.equivalent_stop_days(
        exp_component, base_days, df["sector_vulnerability"].to_numpy(), multiplier
    )
    sp = calibration.supply_shock(stop_days, max_sp, working_days)
    sd = calibration.demand_shock(sp, lam, max_sd)

    out = pd.DataFrame(
        {
            "scenario_id": scenario["scenario_id"],
            "hazard": hazard,
            "severity": severity,
            "province_code": df["province_code"].to_numpy(),
            "region_code": df["region_code"].to_numpy(),
            "province_name": df["province_name"].to_numpy(),
            "province_abbr": df["province_abbr"].to_numpy(),
            "sector_code": df["sector_code"].to_numpy(),
            "macrosector_code": df["macrosector_code"].to_numpy(),
            "node_id": df["node_id"].to_numpy(),
            "raw_exposure": df["raw_exposure"].to_numpy(),
            "exposure_weight": df["exposure_weight"].to_numpy(),
            "sector_vulnerability": df["sector_vulnerability"].to_numpy(),
            "base_interruption_days": base_days,
            "scenario_intensity_multiplier": multiplier,
            "equivalent_stop_days": stop_days,
            "working_days": working_days,
            "supply_shock": sp,
            "demand_pass_through_lambda": lam,
            "demand_shock": sd,
            "max_supply_shock": max_sp,
            "max_demand_shock": max_sd,
            "shock_method": SHOCK_METHOD,
        }
    )
    return out


def _validate(matrix: pd.DataFrame, scenarios: pd.DataFrame, nodes: pd.DataFrame) -> None:
    n_nodes = len(nodes)
    n_scenarios = len(scenarios)

    expected = n_nodes * n_scenarios
    if len(matrix) != expected:
        raise ValueError(
            f"Shock matrix has {len(matrix)} rows, expected "
            f"{expected} ({n_scenarios} scenarios x {n_nodes} nodes)."
        )

    # Every node appears once per scenario.
    per_scenario = matrix.groupby("scenario_id")["node_id"].nunique()
    bad = per_scenario[per_scenario != n_nodes]
    if not bad.empty:
        raise ValueError(
            "Some scenarios do not cover every productive node:\n"
            f"{bad.to_string()}"
        )

    for col in ("supply_shock", "demand_shock", "equivalent_stop_days"):
        if matrix[col].isna().any():
            raise ValueError(f"Shock matrix column '{col}' has null values.")

    if (matrix["supply_shock"] < 0).any() or (matrix["demand_shock"] < 0).any():
        raise ValueError("Shock matrix has negative shock values.")
    if (matrix["supply_shock"] > matrix["max_supply_shock"] + 1e-9).any():
        raise ValueError("Some supply_shock values exceed max_supply_shock.")
    if (matrix["demand_shock"] > matrix["max_demand_shock"] + 1e-9).any():
        raise ValueError("Some demand_shock values exceed max_demand_shock.")
