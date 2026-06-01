"""Consolidate per-scenario simulation results into static dashboard files.

These files are frontend-ready and require no live model execution. They simply
stack and lightly reshape the per-scenario outputs written by
:mod:`batch_runner`.

Outputs (under ``<dashboard_dir>/``)::

    scenario_index.json
    kpi_summary.csv
    province_losses.csv
    sector_losses.csv
    province_sector_losses.csv
    top_penalized_flows.csv
    top_favored_flows.csv
    province_flow_heatmap.csv
    sector_flow_heatmap.csv
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pandas as pd

# Files copied/stacked from each scenario folder, keyed by output basename.
_STACKED_TABLES = {
    "province_losses.csv": "province_results.csv",
    "sector_losses.csv": "sector_results.csv",
    "top_penalized_flows.csv": "top_penalized_flows.csv",
    "top_favored_flows.csv": "top_favored_flows.csv",
    "province_flow_heatmap.csv": "province_flow_heatmap.csv",
    "sector_flow_heatmap.csv": "sector_flow_heatmap.csv",
}


def _scenario_dirs(simulations_dir: Path) -> List[Path]:
    dirs = sorted(
        d for d in Path(simulations_dir).iterdir()
        if d.is_dir() and (d / "scenario_summary.json").exists()
    )
    if not dirs:
        raise FileNotFoundError(
            f"No scenario result folders found under {simulations_dir}. Run "
            "scripts/run_static_scenarios.py first."
        )
    return dirs


def _read_summary(scenario_dir: Path) -> dict:
    with (scenario_dir / "scenario_summary.json").open(encoding="utf-8") as fh:
        return json.load(fh)


def build_dashboard_outputs(simulations_dir: Path, dashboard_dir: Path) -> List[str]:
    """Build all consolidated dashboard files; return the written paths."""
    simulations_dir = Path(simulations_dir)
    dashboard_dir = Path(dashboard_dir)
    dashboard_dir.mkdir(parents=True, exist_ok=True)

    scenario_dirs = _scenario_dirs(simulations_dir)
    summaries = [_read_summary(d) for d in scenario_dirs]
    written: List[str] = []

    # ---- scenario_index.json ----
    index = {
        "n_scenarios": len(summaries),
        "scenarios": [s["scenario_id"] for s in summaries],
        "generated_files": list(_STACKED_TABLES) + ["kpi_summary.csv",
                                                     "province_sector_losses.csv"],
        "note": (
            "Static dashboard export. Generated from precomputed scenario "
            "simulations; no live model execution required."
        ),
        "summaries": summaries,
    }
    index_path = dashboard_dir / "scenario_index.json"
    with index_path.open("w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2)
    written.append(str(index_path))

    # ---- kpi_summary.csv ----
    kpi = pd.DataFrame(summaries)
    kpi_path = dashboard_dir / "kpi_summary.csv"
    kpi.to_csv(kpi_path, index=False)
    written.append(str(kpi_path))

    # ---- Stacked per-scenario tables (tagged with scenario_id) ----
    for out_name, src_name in _STACKED_TABLES.items():
        frames = []
        for scenario_dir in scenario_dirs:
            src = scenario_dir / src_name
            if not src.exists():
                continue
            df = pd.read_csv(src)
            df.insert(0, "scenario_id", scenario_dir.name)
            frames.append(df)
        combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        out_path = dashboard_dir / out_name
        combined.to_csv(out_path, index=False)
        written.append(str(out_path))

    # ---- province_sector_losses.csv (node-level, lightly trimmed) ----
    ps_frames = []
    keep = [
        "scenario_id",
        "node_id",
        "region_code",
        "province_code",
        "sector_code",
        "macrosector_code",
        "x_pre",
        "x_post",
        "direct_loss",
        "indirect_loss",
        "total_loss",
        "loss_rate",
        "supply_shock",
        "demand_shock",
    ]
    for scenario_dir in scenario_dirs:
        src = scenario_dir / "node_results.csv"
        if not src.exists():
            continue
        df = pd.read_csv(src)
        present = [c for c in keep if c in df.columns]
        ps_frames.append(df[present])
    ps_combined = (
        pd.concat(ps_frames, ignore_index=True) if ps_frames else pd.DataFrame()
    )
    ps_path = dashboard_dir / "province_sector_losses.csv"
    ps_combined.to_csv(ps_path, index=False)
    written.append(str(ps_path))

    return written
