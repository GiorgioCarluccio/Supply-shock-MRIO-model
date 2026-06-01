# Shock calibration and static scenario pipeline

This document describes how hazard exposure data is turned into model-ready
supply and demand shock vectors, and how the static scenario library is run and
exported. The pipeline lives in `src/climate_risk_io/shocks/` and is driven by
the scripts in `scripts/` (see the README for the command sequence).

The model estimates **business interruption**, not physical asset damage. The
output is a per-node loss decomposition, not a damage cost.

## 1. Productive nodes and shock vectors

The model operates on productive SAM nodes indexed by `region × sector`. Each
run consumes two vectors of length `n_nodes`:

```text
sp = supply shock vector  (reduction in productive capacity)
sd = demand shock vector  (reduction in final demand)

X_cap   = X0  * (1 - sp)
FD_post = FD0 * (1 - sd)
```

There are **6,462 productive nodes** (107 NUTS-3 provinces × the productive
sectors present in each).

## 2. Core calibration principle

Hazard exposure is **not** directly equal to output loss. Exposure is first
converted into *equivalent operational interruption days*, then into shocks:

```text
equivalent_stop_days = exposure_component
                     × base_interruption_days
                     × sector_vulnerability
                     × scenario_intensity_multiplier

supply_shock = min(equivalent_stop_days / working_days, max_supply_shock)
demand_shock = min(demand_pass_through_lambda × supply_shock, max_demand_shock)
```

with `working_days = 250`. The caps are conservative and editable; defaults are
`max_supply_shock = 0.25` and `max_demand_shock = 0.10`.

The `exposure_component` differs by hazard (see below).

## 3. Heatwave calibration

Source: `data/processed/climate/province_heatwave_indicators.csv` (unchanged;
its methodology is documented in the README).

* `exposure_component = heatwave_exposure_weight[p]` — the validated, attenuated
  relative-exposure multiplier (clipped to `[0.10, 3.00]`).
* `base_interruption_days[heatwave, central] = 5`.

```text
equivalent_stop_days[p, s] = 5 × heatwave_exposure_weight[p]
                               × sector_vulnerability[s, heatwave]
                               × scenario_intensity_multiplier
```

An alternative `heatwave_raw_days_mode` (interpreting raw hot days × a
day-to-stop-day factor) is described in the calibration prompt but the MVP uses
the `base_interruption_days × exposure_weight` central mode above.

## 4. Flood calibration

Source: `data/raw/ispra/province_pir.xlsx` → `province_pir_clean.csv`.

ISPRA local-unit exposure shares map to severities:

```text
flood_high   -> imidp3_p
flood_medium -> imidp2_p
flood_low    -> imidp1_p
```

* `exposure_component = impacted_business_share[p, severity]` (raw share in
  `[0, 1]`, **not** the normalised weight).
* Editable default base days: `flood_low = 3`, `flood_medium = 10`,
  `flood_high = 20`.

## 5. Landslide calibration

Source: same ISPRA workbook.

```text
landslide_p4 -> imfrp4_p
landslide_p3 -> imfrp3_p
landslide_p2 -> imfrp2_p
landslide_p1 -> imfrp1_p
```

* `exposure_component = impacted_business_share[p, severity]`.
* Editable default base days: `landslide_p1 = 2`, `landslide_p2 = 5`,
  `landslide_p3 = 10`, `landslide_p4 = 20`.

## 6. Unit handling for ISPRA shares

ISPRA metadata labels mention percentages, but the observed values are stored as
fractions in `[0, 1]`. The parser validates units per column rather than
blindly dividing by 100:

```text
if max(value) <= 1.5: treat as share in [0, 1]
else:                 treat as percentage and divide by 100
```

## 7. Equivalent stop days

`equivalent_stop_days` is a **scenario assumption**, not an observed loss. It
expresses "how many full-stop-equivalent days of business interruption this
hazard/severity is assumed to cause for this sector in this province", before
conversion into a share of annual capacity.

## 8. Supply and demand shock formulas

```text
supply_shock = min(equivalent_stop_days / 250, max_supply_shock)
demand_shock = min(demand_pass_through_lambda × supply_shock, max_demand_shock)
```

Demand shocks are derived as a **hazard-specific fraction** of supply shocks:

```text
demand_pass_through_lambda: heatwave = 0.10, flood = 0.25, landslide = 0.15
```

## 9. Sector vulnerability

`data/processed/shocks/sector_hazard_vulnerability.csv` holds an editable
`sector × hazard` multiplier. Defaults are placeholders keyed on the three
macrosectors (A = agriculture, I = industry, S = services):

| hazard    | macrosector A | macrosector I | macrosector S |
|-----------|---------------|---------------|---------------|
| heatwave  | 0.70          | 0.40          | 0.30          |
| flood     | 0.70          | 0.80          | 0.50          |
| landslide | 0.50          | 0.45          | 0.35          |

These are **expert-placeholder assumptions, not empirically estimated values**,
and are meant to be edited.

## 10. Province-code crosswalk

Climate exposure files use ISTAT numeric province codes (`cod_prov`); the
productive SAM nodes use NUTS-3 2021 region codes (`ITC11`, …). The two systems
are **not** assumed to be equal. A crosswalk is built and written to
`data/processed/mappings/province_code_crosswalk.csv` with columns
`province_code, province_name, province_abbr, region_code`.

The crosswalk is built from an embedded NUTS-3 → car-plate-abbreviation
reference joined to the authoritative ISTAT provinces layer
(`istat_provinces_2024.gpkg`), and validated to be a bijection over the 107
provinces. The shock-matrix step **requires** this crosswalk and fails with an
actionable error if it is missing. If a deployment ever uses SAM region codes
that already equal ISTAT province codes, that must be opted into explicitly via
`--region-code-equals-province`; it is never assumed silently.

## 11. Scenario library

`data/processed/shocks/scenario_library.csv` fixes the calibration knobs per
`hazard × severity`. The central dashboard set (`is_dashboard_scenario = True`):

```text
heatwave_central
flood_low, flood_medium, flood_high
landslide_p1, landslide_p2, landslide_p3, landslide_p4
```

Each row carries `base_interruption_days`, `scenario_intensity_multiplier`,
`demand_pass_through_lambda`, `max_supply_shock` and `max_demand_shock`. Edit the
CSV to add conservative / stress variants or to retune.

## 12. Shock matrix

`data/processed/shocks/shock_matrix.csv` has one row per `scenario × productive
node`, joining exposure, vulnerability, scenario knobs, nodes and the crosswalk.
The builder validates that every productive node receives exactly one shock per
scenario, that there are no null shocks, and that shocks respect the caps.

## 13. Static simulation and dashboard export

`run_static_scenarios.py` builds the `sp` / `sd` vectors for each dashboard
scenario and runs the reference propagation model, writing per-scenario tables
(node / province / sector results, top penalised / favoured flows, province and
sector flow heatmaps, and a summary JSON) under
`data/processed/simulations/<scenario_id>/`.

`build_dashboard_outputs.py` consolidates those into static, frontend-ready
files under `data/processed/dashboard/` (a scenario index, a KPI summary, and
stacked province / sector / flow tables). These files require no live model
execution.

## 14. Limitations

1. **Calibration is assumption-driven.** Equivalent stop days, base interruption
   days, vulnerability multipliers and pass-through lambdas are expert
   placeholders, not estimated parameters. They are deliberately editable.
2. **Exposure ≠ loss.** Flood / landslide use the *share of local business
   units at risk*, not a probability of interruption; heatwave uses a relative
   exposure weight. Both are proxies.
3. **Single-hazard scenarios.** The dashboard scenarios are independent; they
   are not combined into compound events.
4. **Downstream model behaviour.** The shock-calibration layer is independent of
   the propagation model. The committed propagation model is the strict-min
   reference model with the aggregated global-feasibility cap always on; on the
   full economy it over-propagates and does not converge within the iteration
   budget (total/direct multiplier well above the ~2–3 sanity range), as
   documented in [model_layer.md](model_layer.md) §5 and the project notes.
   Simulation totals therefore inherit that known, deferred model issue —
   interpret them as upper-bound, not converged, estimates until the
   propagation channel is finalised. The shock vectors themselves are
   conservative (capped at a 25% capacity reduction) and validated.
