"""Shock calibration and static scenario pipeline.

This package turns hazard exposure data (heatwave, flood, landslide) into
model-ready supply and demand shock vectors, runs a fixed library of
precomputed scenarios through the reference IO propagation model, and exports
dashboard-ready result tables.

The pipeline is deliberately simple, explicit and local. It has no web app, no
FastAPI/Next.js/Docker, no database and no cloud dependency. Every step reads
and writes plain CSV / JSON / NumPy files under ``data/processed``.

Stages
------
1. ``pir_parser``           parse the raw ISPRA PIR workbook into a clean table.
2. ``exposure_loader``      build the province crosswalk and the canonical
                            hazard exposure table.
3. ``sector_vulnerability`` build the editable sector x hazard vulnerability
                            table.
4. ``scenario_library``     build the static scenario library.
5. ``calibration``          core formulas: exposure -> equivalent stop days ->
                            supply / demand shocks.
6. ``shock_matrix``         assemble the node-level shock matrix.
7. ``batch_runner``         run the model for each dashboard scenario.
8. ``dashboard_exports``    consolidate simulation results into static files.

Assumptions (see ``docs/methodology/shock_calibration.md``)
-----------------------------------------------------------
* ISPRA flood / landslide values are treated as shares in ``[0, 1]`` when their
  maximum is ``<= 1.5`` (otherwise as percentages divided by 100).
* Flood / landslide raw exposure is the share of local business units at risk.
* Heatwave uses the validated ``heatwave_exposure_weight``.
* Equivalent stop days are *scenario assumptions*, not observed losses.
* Sector vulnerability defaults are expert placeholders and must stay editable.
* Demand shocks are a hazard-specific fraction of supply shocks.
* Generated dashboard files are static and do not require live model execution.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Hazard / severity vocabulary
# --------------------------------------------------------------------------- #
HEATWAVE = "heatwave"
FLOOD = "flood"
LANDSLIDE = "landslide"

HAZARDS = (HEATWAVE, FLOOD, LANDSLIDE)

# Macrosector codes used by the productive SAM nodes.
MACROSECTORS = ("A", "I", "S")

# Number of effective working days used to turn equivalent stop days into a
# share of annual productive capacity.
WORKING_DAYS = 250

# Conservative, editable shock caps.
MAX_SUPPLY_SHOCK = 0.25
MAX_DEMAND_SHOCK = 0.10

# Attenuation used only for the *visualisation* exposure weight of flood and
# landslide (the shock formula uses the raw impacted-business share).
EXPOSURE_WEIGHT_ATTENUATION = 0.50
EXPOSURE_WEIGHT_CLIP = (0.10, 3.00)

__all__ = [
    "HEATWAVE",
    "FLOOD",
    "LANDSLIDE",
    "HAZARDS",
    "MACROSECTORS",
    "WORKING_DAYS",
    "MAX_SUPPLY_SHOCK",
    "MAX_DEMAND_SHOCK",
    "EXPOSURE_WEIGHT_ATTENUATION",
    "EXPOSURE_WEIGHT_CLIP",
]
