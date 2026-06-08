"""Export precomputed dashboard outputs into frontend-ready static JSON assets.

This script does NOT run the model. It reads already-generated files from
``data/processed/`` and converts them into compact, per-scenario JSON files
that the static Next.js dashboard loads client-side.

Inputs (precomputed):
    data/processed/dashboard/scenario_index.json
    data/processed/dashboard/kpi_summary.csv
    data/processed/dashboard/province_losses.csv
    data/processed/dashboard/sector_losses.csv
    data/processed/dashboard/province_sector_losses.csv
    data/processed/dashboard/top_penalized_flows.csv
    data/processed/dashboard/top_favored_flows.csv
    data/processed/dashboard/province_flow_heatmap.csv
    data/processed/dashboard/sector_flow_heatmap.csv
    data/processed/climate/province_hazard_exposure.csv
    data/processed/shocks/shock_matrix.csv
    data/processed/shocks/sector_hazard_vulnerability.csv
    data/processed/shocks/scenario_library.csv
    data/processed/mappings/province_code_crosswalk.csv
    data/processed/model_inputs/sector_mapping.csv

Outputs (written to frontend/public/data/):
    scenario_index.json                       enriched scenario tree + caveats
    kpi_summary.json                          array of per-scenario KPIs
    crosswalk.json                            province_code <-> region_code map
    sector_meta.json                          sector_code -> macrosector + label
    sector_hazard_vulnerability.json
    province_hazard_exposure.json
    data_status.json                          generation status / runtime caveat
    province_metrics/<scenario>.json          merged province map/regional metrics
    sector_losses/<scenario>.json
    province_sector_losses/<scenario>.json    region x sector node losses
    top_penalized_flows/<scenario>.json
    top_favored_flows/<scenario>.json
    province_flow_heatmap/<scenario>.json
    sector_flow_heatmap/<scenario>.json

Usage (from repo root):
    .venv/Scripts/python.exe scripts/export_dashboard_data_for_frontend.py

The generated frontend/public/data directory can be large; it is meant to be
regenerated with this script rather than committed (see frontend/public/data/.gitignore).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DASH = REPO_ROOT / "data" / "processed" / "dashboard"
CLIMATE = REPO_ROOT / "data" / "processed" / "climate"
SHOCKS = REPO_ROOT / "data" / "processed" / "shocks"
MAPPINGS = REPO_ROOT / "data" / "processed" / "mappings"
MODEL_INPUTS = REPO_ROOT / "data" / "processed" / "model_inputs"
OUT = REPO_ROOT / "frontend" / "public" / "data"

# Optional NACE sector_code -> full sector name decoder (2 columns, no header:
# code, name). Used to enrich sector_meta.json with human-readable labels for
# the dashboard. If absent, sector_name is simply omitted (graceful fallback).
SECTOR_DECODER_PATH = REPO_ROOT / "eurostat_sector_decoder.xlsx"

# Runtime parameters the dashboard scenarios are *expected* to use.
EXPECTED_MAX_ITER = 1
EXPECTED_GAMMA = 0.5


def _require(path: Path) -> Path:
    if not path.exists():
        print(f"ERROR: required input missing: {path}", file=sys.stderr)
        raise SystemExit(1)
    return path


def _clean(obj):
    """Make values JSON-safe: NaN/inf -> None, numpy scalars -> python."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


def _records(df: pd.DataFrame) -> list[dict]:
    df = df.where(pd.notnull(df), None)
    recs = df.to_dict("records")
    out = []
    for r in recs:
        out.append({k: _clean(v) for k, v in r.items()})
    return out


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))


def _write_per_scenario(df: pd.DataFrame, subdir: str, scenario_col: str = "scenario_id") -> int:
    """Split a long dataframe into one compact JSON file per scenario."""
    out_dir = OUT / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for scenario_id, group in df.groupby(scenario_col):
        _write_json(out_dir / f"{scenario_id}.json", _records(group))
        n += 1
    return n


def main() -> int:
    print(f"Repo root: {REPO_ROOT}")
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- crosswalk -------------------------------------------------------
    # keep_default_na=False so plate codes like "NA" (Napoli) survive as the
    # string "NA" instead of being coerced to NaN by pandas' default NA list.
    xwalk = pd.read_csv(
        _require(MAPPINGS / "province_code_crosswalk.csv"),
        keep_default_na=False,
        na_values=[""],
    )
    xwalk["province_code"] = xwalk["province_code"].astype(int)
    _write_json(OUT / "crosswalk.json", _records(xwalk))
    region_to_meta = xwalk.set_index("region_code").to_dict("index")
    print(f"  crosswalk: {len(xwalk)} provinces")

    # ---- scenario index + KPIs ------------------------------------------
    scenario_index = json.loads(_require(DASH / "scenario_index.json").read_text(encoding="utf-8"))
    kpi = pd.read_csv(_require(DASH / "kpi_summary.csv"))
    kpi_records = _records(kpi)
    _write_json(OUT / "kpi_summary.json", kpi_records)

    # Validate runtime parameters and build a caveat if they differ.
    iters = sorted({int(r["iterations"]) for r in kpi_records if r.get("iterations") is not None})
    runtime_matches_expected = iters == [EXPECTED_MAX_ITER]
    runtime_caveat = None
    if not runtime_matches_expected:
        runtime_caveat = (
            "Scenario outputs are static demonstrative results. The dashboard "
            f"specification expects max_iter = {EXPECTED_MAX_ITER} and gamma = {EXPECTED_GAMMA}, "
            f"but the stored scenario build report records iterations = {iters}. "
            "Runtime parameters should be verified in the scenario build report."
        )
        print(f"  WARNING: iterations in outputs = {iters} (expected {EXPECTED_MAX_ITER})")

    # Build a hazard -> [scenarios] tree for the selector UI.
    summaries = scenario_index.get("summaries", [])
    hazards: dict[str, list] = {}
    for s in summaries:
        hazards.setdefault(s["hazard"], []).append(
            {"scenario_id": s["scenario_id"], "severity": s.get("severity")}
        )
    enriched_index = {
        **scenario_index,
        "hazards": [
            {"hazard": h, "scenarios": sc} for h, sc in hazards.items()
        ],
        "expected_runtime": {"max_iter": EXPECTED_MAX_ITER, "gamma": EXPECTED_GAMMA},
        "runtime_matches_expected": runtime_matches_expected,
        "runtime_caveat": runtime_caveat,
    }
    _write_json(OUT / "scenario_index.json", enriched_index)
    print(f"  scenarios: {len(summaries)} across {len(hazards)} hazards")

    # ---- sector metadata -------------------------------------------------
    sector_map = pd.read_csv(_require(MODEL_INPUTS / "sector_mapping.csv"))
    # Enrich with full NACE sector names from the decoder if available. The
    # decoder has no header row: column 0 = sector_code, column 1 = full name.
    if SECTOR_DECODER_PATH.exists():
        decoder = pd.read_excel(
            SECTOR_DECODER_PATH, header=None, names=["sector_code", "sector_name"]
        )
        decoder["sector_code"] = decoder["sector_code"].astype(str).str.strip()
        sector_map["sector_code"] = sector_map["sector_code"].astype(str).str.strip()
        sector_map = sector_map.merge(decoder, on="sector_code", how="left")
        n_missing = int(sector_map["sector_name"].isna().sum())
        if n_missing:
            missing = sector_map.loc[sector_map["sector_name"].isna(), "sector_code"].tolist()
            print(f"  WARNING: {n_missing} sector(s) without a decoder name: {missing}")
        else:
            print(f"  sector_meta: enriched {len(sector_map)} sectors with full names")
    else:
        print(f"  NOTE: sector decoder not found at {SECTOR_DECODER_PATH}; "
              "sector_name omitted from sector_meta.json")
    _write_json(OUT / "sector_meta.json", _records(sector_map))

    vuln = pd.read_csv(_require(SHOCKS / "sector_hazard_vulnerability.csv"))
    _write_json(OUT / "sector_hazard_vulnerability.json", _records(vuln))

    # ---- province hazard exposure ---------------------------------------
    # keep_default_na=False to preserve the "NA" (Napoli) plate code.
    exposure = pd.read_csv(
        _require(CLIMATE / "province_hazard_exposure.csv"),
        keep_default_na=False,
        na_values=[""],
    )
    _write_json(OUT / "province_hazard_exposure.json", _records(exposure))
    print(f"  province_hazard_exposure: {len(exposure)} rows")

    # ---- aggregate shock_matrix to province x scenario ------------------
    shock = pd.read_csv(_require(SHOCKS / "shock_matrix.csv"))
    shock_prov = (
        shock.groupby(["scenario_id", "region_code"])
        .agg(
            province_code=("province_code", "first"),
            province_name=("province_name", "first"),
            province_abbr=("province_abbr", "first"),
            raw_exposure=("raw_exposure", "mean"),
            exposure_weight=("exposure_weight", "mean"),
            equivalent_stop_days=("equivalent_stop_days", "mean"),
            base_interruption_days=("base_interruption_days", "first"),
            mean_supply_shock=("supply_shock", "mean"),
            max_supply_shock=("supply_shock", "max"),
            mean_demand_shock=("demand_shock", "mean"),
            max_demand_shock=("demand_shock", "max"),
        )
        .reset_index()
    )

    # ---- province losses + merge into province_metrics per scenario ------
    plosses = pd.read_csv(_require(DASH / "province_losses.csv"))
    # indirect ratio with divide-by-zero protection
    plosses["indirect_exposure_ratio"] = plosses.apply(
        lambda r: (r["total_loss"] - r["direct_loss"]) / r["total_loss"]
        if r["total_loss"] not in (0, None) and not pd.isna(r["total_loss"]) and r["total_loss"] != 0
        else 0.0,
        axis=1,
    )

    # province_losses already carries the canonical province-level supply-shock
    # mean/max; drop the duplicates from the aggregated shock frame to avoid
    # _x/_y suffixed columns after the merge.
    metrics = plosses.merge(
        shock_prov.drop(
            columns=[
                "province_code",
                "province_name",
                "province_abbr",
                "mean_supply_shock",
                "max_supply_shock",
            ]
        ),
        on=["scenario_id", "region_code"],
        how="left",
    )
    # attach province identity from crosswalk
    metrics["province_code"] = metrics["region_code"].map(
        lambda rc: region_to_meta.get(rc, {}).get("province_code")
    )
    metrics["province_name"] = metrics["region_code"].map(
        lambda rc: region_to_meta.get(rc, {}).get("province_name")
    )
    metrics["province_abbr"] = metrics["region_code"].map(
        lambda rc: region_to_meta.get(rc, {}).get("province_abbr")
    )
    n = _write_per_scenario(metrics, "province_metrics")
    print(f"  province_metrics: {n} scenario files ({len(metrics)} rows total)")

    # ---- sector losses (per scenario) -----------------------------------
    slosses = pd.read_csv(_require(DASH / "sector_losses.csv"))
    n = _write_per_scenario(slosses, "sector_losses")
    print(f"  sector_losses: {n} scenario files")

    # ---- province-sector losses (per scenario, region x sector nodes) ----
    psl = pd.read_csv(_require(DASH / "province_sector_losses.csv"))
    n = _write_per_scenario(psl, "province_sector_losses")
    print(f"  province_sector_losses: {n} scenario files ({len(psl)} rows total)")

    # ---- flows (per scenario) -------------------------------------------
    pen = pd.read_csv(_require(DASH / "top_penalized_flows.csv"))
    n = _write_per_scenario(pen, "top_penalized_flows")
    print(f"  top_penalized_flows: {n} scenario files")

    fav = pd.read_csv(_require(DASH / "top_favored_flows.csv"))
    n = _write_per_scenario(fav, "top_favored_flows")
    print(f"  top_favored_flows: {n} scenario files")

    # ---- heatmaps (per scenario) ----------------------------------------
    pheat = pd.read_csv(_require(DASH / "province_flow_heatmap.csv"))
    n = _write_per_scenario(pheat, "province_flow_heatmap")
    print(f"  province_flow_heatmap: {n} scenario files ({len(pheat)} rows total)")

    sheat = pd.read_csv(_require(DASH / "sector_flow_heatmap.csv"))
    n = _write_per_scenario(sheat, "sector_flow_heatmap")
    print(f"  sector_flow_heatmap: {n} scenario files")

    # ---- data status card ------------------------------------------------
    geojson = OUT / "geographies" / "italy_provinces.geojson"
    status = {
        "climate_exposure": "processed",
        "shock_calibration": "processed",
        "sam_model_inputs": "processed",
        "simulation_outputs": "static",
        "frontend_mode": "static demo",
        "geojson_present": geojson.exists(),
        "n_scenarios": len(summaries),
        "iterations_in_outputs": iters,
        "expected_max_iter": EXPECTED_MAX_ITER,
        "expected_gamma": EXPECTED_GAMMA,
        "runtime_matches_expected": runtime_matches_expected,
        "runtime_caveat": runtime_caveat,
    }
    _write_json(OUT / "data_status.json", status)

    print("\nDONE. Frontend data written to:", OUT)
    if not geojson.exists():
        print(
            "  NOTE: province GeoJSON not found. Run "
            "scripts/export_province_geojson_for_frontend.py to generate it."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
