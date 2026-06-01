"""Lightweight validation for the static dashboard data export.

Checks that the precomputed inputs exist, that the export produced the expected
frontend JSON assets, and that the key joins the dashboard relies on actually
hold (province codes vs GeoJSON, shock records vs province/sector records).

Run AFTER the two export scripts:
    .venv/Scripts/python.exe scripts/export_province_geojson_for_frontend.py
    .venv/Scripts/python.exe scripts/export_dashboard_data_for_frontend.py
    .venv/Scripts/python.exe scripts/test_frontend_data_export.py

Exits non-zero on the first hard failure so it can gate CI / manual checks.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DASH = REPO_ROOT / "data" / "processed" / "dashboard"
CLIMATE = REPO_ROOT / "data" / "processed" / "climate"
SHOCKS = REPO_ROOT / "data" / "processed" / "shocks"
OUT = REPO_ROOT / "frontend" / "public" / "data"

_failures: list[str] = []
_passes = 0


def check(cond: bool, msg: str) -> None:
    global _passes
    if cond:
        _passes += 1
        print(f"  PASS  {msg}")
    else:
        _failures.append(msg)
        print(f"  FAIL  {msg}")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    print("== Required processed inputs exist ==")
    for p in [
        DASH / "scenario_index.json",
        DASH / "kpi_summary.csv",
        DASH / "province_losses.csv",
        DASH / "sector_losses.csv",
        DASH / "province_sector_losses.csv",
        CLIMATE / "province_hazard_exposure.csv",
        SHOCKS / "shock_matrix.csv",
    ]:
        check(p.exists(), f"input present: {p.relative_to(REPO_ROOT)}")

    print("\n== Exported frontend assets exist ==")
    scenario_index_path = OUT / "scenario_index.json"
    check(scenario_index_path.exists(), "scenario_index.json exported")
    for f in [
        "kpi_summary.json",
        "crosswalk.json",
        "sector_meta.json",
        "province_hazard_exposure.json",
        "data_status.json",
    ]:
        check((OUT / f).exists(), f"{f} exported")

    geojson_path = OUT / "geographies" / "italy_provinces.geojson"
    check(geojson_path.exists(), "province GeoJSON exported")

    if not scenario_index_path.exists():
        print("\nABORT: scenario_index.json missing; run the export scripts first.")
        return 1

    index = load_json(scenario_index_path)
    scenarios = index.get("scenarios", [])
    print("\n== Scenario index ==")
    check(len(scenarios) >= 1, f"at least one scenario available ({len(scenarios)} found)")

    print("\n== Per-scenario files exist for every scenario ==")
    per_scenario_dirs = [
        "province_metrics",
        "sector_losses",
        "province_sector_losses",
        "top_penalized_flows",
        "top_favored_flows",
        "province_flow_heatmap",
        "sector_flow_heatmap",
    ]
    for sub in per_scenario_dirs:
        missing = [s for s in scenarios if not (OUT / sub / f"{s}.json").exists()]
        check(not missing, f"{sub}: all {len(scenarios)} scenario files present"
              + ("" if not missing else f" (missing: {missing})"))

    if not geojson_path.exists():
        print("\nABORT: GeoJSON missing; cannot validate joins.")
        return 1

    print("\n== GeoJSON is strictly valid JSON (no NaN/Infinity tokens) ==")
    raw_geo = geojson_path.read_text(encoding="utf-8")
    has_bad_tokens = any(
        tok in raw_geo for tok in ("NaN", "Infinity", "-Infinity")
    )
    check(
        not has_bad_tokens,
        "GeoJSON has no bare NaN/Infinity tokens (would break browser JSON.parse)",
    )
    try:
        # json.loads with default settings rejects NaN only if parse_constant
        # raises; emulate the browser by disallowing those constants.
        json.loads(raw_geo, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
        browser_parseable = True
    except ValueError:
        browser_parseable = False
    check(browser_parseable, "GeoJSON parses under strict (browser-like) JSON rules")

    print("\n== Province losses join with GeoJSON region codes ==")
    geo = load_json(geojson_path)
    check(
        all(f["properties"].get("province_abbr") for f in geo["features"]),
        "every GeoJSON feature has a non-empty province_abbr",
    )
    geo_region_codes = {
        f["properties"].get("region_code") for f in geo["features"]
    }
    sample_scenario = scenarios[0]
    metrics = load_json(OUT / "province_metrics" / f"{sample_scenario}.json")
    metric_regions = {r["region_code"] for r in metrics}
    joinable = metric_regions & geo_region_codes
    coverage = len(joinable) / max(len(metric_regions), 1)
    check(
        coverage >= 0.95,
        f"province_metrics ({sample_scenario}) region_codes join GeoJSON: "
        f"{len(joinable)}/{len(metric_regions)} ({coverage:.0%})",
    )

    print("\n== Province metrics carry province identity (crosswalk join) ==")
    with_name = [r for r in metrics if r.get("province_name")]
    check(
        len(with_name) == len(metrics),
        f"all province_metrics rows resolved a province_name "
        f"({len(with_name)}/{len(metrics)})",
    )

    print("\n== Shock records join province + sector node records ==")
    psl = load_json(OUT / "province_sector_losses" / f"{sample_scenario}.json")
    check(len(psl) > 0, f"province_sector_losses ({sample_scenario}) non-empty")
    psl_regions = {r["region_code"] for r in psl}
    check(
        psl_regions <= geo_region_codes | metric_regions,
        "province_sector_losses region_codes are known provinces",
    )
    sectors_meta = {r["sector_code"] for r in load_json(OUT / "sector_meta.json")}
    psl_sectors = {r["sector_code"] for r in psl}
    check(
        psl_sectors <= sectors_meta,
        f"province_sector_losses sectors are known sectors "
        f"({len(psl_sectors & sectors_meta)}/{len(psl_sectors)})",
    )

    print("\n== Critical numeric fields are not entirely null ==")
    for field in ("total_loss", "direct_loss", "indirect_loss", "loss_rate"):
        non_null = [r for r in metrics if r.get(field) is not None]
        check(len(non_null) > 0, f"province_metrics.{field} has non-null values")

    print("\n== Summary ==")
    print(f"  {_passes} checks passed, {len(_failures)} failed")
    if _failures:
        print("\nFAILED CHECKS:")
        for f in _failures:
            print(f"  - {f}")
        return 1
    print("  All validation checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
