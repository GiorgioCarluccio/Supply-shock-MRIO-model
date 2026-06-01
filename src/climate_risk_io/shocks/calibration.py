"""Core shock calibration formulas.

Hazard exposure is not directly equal to output loss. The calibration converts
exposure into *equivalent operational interruption days*, then into supply and
demand shocks expressed as shares of annual productive capacity / final demand.

For a province ``p``, sector ``s``, hazard ``h`` and severity::

    equivalent_stop_days = exposure_component
                         * base_interruption_days
                         * sector_vulnerability
                         * scenario_intensity_multiplier

    supply_shock = min(equivalent_stop_days / working_days, max_supply_shock)
    demand_shock = min(lambda * supply_shock, max_demand_shock)

The ``exposure_component`` differs by hazard:

* heatwave  -> ``heatwave_exposure_weight`` (relative, attenuated multiplier);
* flood     -> ``impacted_business_share`` (raw share in [0, 1]);
* landslide -> ``impacted_business_share`` (raw share in [0, 1]).

All functions are pure and fully vectorised over NumPy / pandas inputs.
"""

from __future__ import annotations

import numpy as np

from . import FLOOD, HEATWAVE, LANDSLIDE, WORKING_DAYS


def exposure_component(hazard, raw_exposure, exposure_weight):
    """Select the exposure measure that drives the shock for ``hazard``.

    Heatwave uses the attenuated relative exposure weight; flood and landslide
    use the raw impacted-business share. Works on scalars or arrays.
    """
    hazard_arr = np.asarray(hazard)
    raw = np.asarray(raw_exposure, dtype=float)
    weight = np.asarray(exposure_weight, dtype=float)
    is_heatwave = hazard_arr == HEATWAVE
    return np.where(is_heatwave, weight, raw)


def equivalent_stop_days(
    exposure_value, base_interruption_days, sector_vulnerability, intensity_multiplier
):
    """Equivalent operational interruption days (a scenario assumption)."""
    return (
        np.asarray(exposure_value, dtype=float)
        * np.asarray(base_interruption_days, dtype=float)
        * np.asarray(sector_vulnerability, dtype=float)
        * np.asarray(intensity_multiplier, dtype=float)
    )


def supply_shock(equivalent_stop_days_value, max_supply_shock, working_days=WORKING_DAYS):
    """Supply shock = capped share of working days lost to interruption."""
    raw = np.asarray(equivalent_stop_days_value, dtype=float) / float(working_days)
    return np.minimum(raw, np.asarray(max_supply_shock, dtype=float))


def demand_shock(supply_shock_value, demand_pass_through_lambda, max_demand_shock):
    """Demand shock = capped hazard-specific fraction of the supply shock."""
    raw = np.asarray(demand_pass_through_lambda, dtype=float) * np.asarray(
        supply_shock_value, dtype=float
    )
    return np.minimum(raw, np.asarray(max_demand_shock, dtype=float))


__all__ = [
    "exposure_component",
    "equivalent_stop_days",
    "supply_shock",
    "demand_shock",
    "HEATWAVE",
    "FLOOD",
    "LANDSLIDE",
]
