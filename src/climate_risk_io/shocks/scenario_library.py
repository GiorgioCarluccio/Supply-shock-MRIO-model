"""Static scenario library.

Each scenario fixes the calibration knobs for one ``hazard x severity``
combination: base interruption days, intensity multiplier, demand pass-through
and shock caps. The central scenario set is flagged ``is_dashboard_scenario``
so the batch runner and dashboard export use a small, well-defined library.
"""

from __future__ import annotations

import pandas as pd

from . import (
    FLOOD,
    HEATWAVE,
    LANDSLIDE,
    MAX_DEMAND_SHOCK,
    MAX_SUPPLY_SHOCK,
)

# Editable default base interruption days per hazard / severity.
BASE_INTERRUPTION_DAYS = {
    (HEATWAVE, "central"): 5,
    (FLOOD, "low"): 3,
    (FLOOD, "medium"): 10,
    (FLOOD, "high"): 20,
    (LANDSLIDE, "p1"): 2,
    (LANDSLIDE, "p2"): 5,
    (LANDSLIDE, "p3"): 10,
    (LANDSLIDE, "p4"): 20,
}

# Editable demand pass-through (share of supply shock that hits final demand).
DEMAND_PASS_THROUGH_LAMBDA = {
    HEATWAVE: 0.10,
    FLOOD: 0.25,
    LANDSLIDE: 0.15,
}

# The central dashboard scenario set: (scenario_id, hazard, severity).
DASHBOARD_SCENARIOS = [
    ("heatwave_central", HEATWAVE, "central"),
    ("flood_low", FLOOD, "low"),
    ("flood_medium", FLOOD, "medium"),
    ("flood_high", FLOOD, "high"),
    ("landslide_p1", LANDSLIDE, "p1"),
    ("landslide_p2", LANDSLIDE, "p2"),
    ("landslide_p3", LANDSLIDE, "p3"),
    ("landslide_p4", LANDSLIDE, "p4"),
]

# Central intensity. Conservative / stress variants can be added by editing the
# generated CSV; only the central set is marked as a dashboard scenario.
CENTRAL_INTENSITY = "central"
CENTRAL_MULTIPLIER = 1.0


def build_scenario_library() -> pd.DataFrame:
    """Build the static scenario library DataFrame."""
    rows = []
    for scenario_id, hazard, severity in DASHBOARD_SCENARIOS:
        rows.append(
            {
                "scenario_id": scenario_id,
                "hazard": hazard,
                "severity": severity,
                "scenario_intensity": CENTRAL_INTENSITY,
                "scenario_intensity_multiplier": CENTRAL_MULTIPLIER,
                "base_interruption_days": BASE_INTERRUPTION_DAYS[(hazard, severity)],
                "demand_pass_through_lambda": DEMAND_PASS_THROUGH_LAMBDA[hazard],
                "max_supply_shock": MAX_SUPPLY_SHOCK,
                "max_demand_shock": MAX_DEMAND_SHOCK,
                "is_dashboard_scenario": True,
            }
        )
    return pd.DataFrame(rows)


def load_scenario_library(path) -> pd.DataFrame:
    """Load the scenario library CSV, validating required columns."""
    from pathlib import Path

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Scenario library not found: {path}. Build it with "
            "scripts/build_scenario_library.py."
        )
    lib = pd.read_csv(path)
    required = {
        "scenario_id",
        "hazard",
        "severity",
        "scenario_intensity_multiplier",
        "base_interruption_days",
        "demand_pass_through_lambda",
        "max_supply_shock",
        "max_demand_shock",
        "is_dashboard_scenario",
    }
    missing = required - set(lib.columns)
    if missing:
        raise ValueError(f"Scenario library is missing columns {sorted(missing)}.")
    lib["scenario_id"] = lib["scenario_id"].astype(str)
    lib["hazard"] = lib["hazard"].astype(str)
    lib["severity"] = lib["severity"].astype(str)
    lib["is_dashboard_scenario"] = lib["is_dashboard_scenario"].astype(bool)
    return lib
