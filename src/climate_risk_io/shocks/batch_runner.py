"""Batch simulation runner for the static scenario library.

For each selected scenario, this module builds the per-node supply / demand
shock vectors from the shock matrix, runs the reference IO propagation model on
the full productive block, and writes the per-scenario result tables that the
dashboard export consumes.

Outputs per scenario (under ``<out_dir>/<scenario_id>/``)::

    scenario_summary.json
    node_results.csv
    province_results.csv
    sector_results.csv
    top_penalized_flows.csv
    top_favored_flows.csv
    province_flow_heatmap.csv
    sector_flow_heatmap.csv
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from climate_risk_io.model import results
from climate_risk_io.model.io_model import IOClimateModel

DEFAULT_GAMMA = 0.5
DEFAULT_MAX_ITER = 50
DEFAULT_TOL = 1e-6
DEFAULT_TOP_N = 100


def build_shock_vectors(scenario_matrix: pd.DataFrame, n_nodes: int) -> Dict[str, np.ndarray]:
    """Build ``sp`` / ``sd`` vectors (length ``n_nodes``) ordered by ``node_id``."""
    ordered = scenario_matrix.sort_values("node_id")
    node_ids = ordered["node_id"].to_numpy()
    if node_ids.shape[0] != n_nodes or not np.array_equal(
        node_ids, np.arange(n_nodes)
    ):
        raise ValueError(
            "Shock matrix node_id values do not form a contiguous 0..n-1 range "
            f"matching the {n_nodes} model nodes."
        )
    sp = np.clip(ordered["supply_shock"].to_numpy(dtype=float), 0.0, 1.0)
    sd = np.clip(ordered["demand_shock"].to_numpy(dtype=float), 0.0, 1.0)
    return {"sp": sp, "sd": sd}


def _aggregate_flows(
    matrix: np.ndarray, group_of: np.ndarray, n_groups: int
) -> np.ndarray:
    """Aggregate an ``n x n`` flow matrix to ``n_groups x n_groups`` by group.

    ``out[a, b]`` sums flows from origin nodes in group ``a`` to destination
    nodes in group ``b``. Done in two cheap passes (rows then columns) to avoid
    materialising the dense ``n*n`` index arrays.
    """
    n = matrix.shape[0]
    rows = np.zeros((n_groups, n), dtype=float)
    np.add.at(rows, group_of, matrix)  # rows[g] = sum of origin rows in group g
    cols = np.zeros((n_groups, n_groups), dtype=float)
    np.add.at(cols, group_of, rows.T)  # cols[g_dest, g_origin]
    return cols.T


def _flow_heatmap_long(
    delta_Z: np.ndarray,
    Z_pre: np.ndarray,
    Z_post: np.ndarray,
    labels: List[str],
    group_of: np.ndarray,
    dimension: str,
) -> pd.DataFrame:
    """Long-format aggregated flow heatmap for a grouping dimension."""
    n_groups = len(labels)
    delta = _aggregate_flows(delta_Z, group_of, n_groups)
    pre = _aggregate_flows(Z_pre, group_of, n_groups)
    post = _aggregate_flows(Z_post, group_of, n_groups)

    origin_idx, dest_idx = np.meshgrid(
        np.arange(n_groups), np.arange(n_groups), indexing="ij"
    )
    label_arr = np.asarray(labels)
    return pd.DataFrame(
        {
            f"origin_{dimension}": label_arr[origin_idx.ravel()],
            f"destination_{dimension}": label_arr[dest_idx.ravel()],
            "pre_value": pre.ravel(),
            "post_value": post.ravel(),
            "delta_value": delta.ravel(),
        }
    )


def _group_indexer(values: pd.Series):
    """Return ``(labels, group_of)`` mapping each row to a contiguous group id."""
    labels = sorted(values.astype(str).unique())
    label_to_id = {label: i for i, label in enumerate(labels)}
    group_of = values.astype(str).map(label_to_id).to_numpy(dtype=np.int64)
    return labels, group_of


def run_scenario(
    scenario: pd.Series,
    scenario_matrix: pd.DataFrame,
    model_inputs: Dict[str, Any],
    out_dir: Path,
    *,
    gamma: float = DEFAULT_GAMMA,
    max_iter: int = DEFAULT_MAX_ITER,
    tol: float = DEFAULT_TOL,
    top_n: int = DEFAULT_TOP_N,
) -> Dict[str, Any]:
    """Run one scenario through the model and write its result tables."""
    nodes = model_inputs["productive_nodes"]
    Z0 = model_inputs["Z0"]
    X0 = model_inputs["X0"]
    FD0 = model_inputs["FD0"]
    globsec_of = model_inputs["globsec_of"]
    n = len(nodes)

    vectors = build_shock_vectors(scenario_matrix, n)
    sp, sd = vectors["sp"], vectors["sd"]

    model = IOClimateModel(
        Z0=Z0,
        FD0=FD0,
        X0=X0,
        sector_group_of=globsec_of,
        node_labels=nodes["node_label"].tolist()
        if "node_label" in nodes.columns
        else None,
    )
    run_output = model.run(sd=sd, sp=sp, gamma=gamma, max_iter=max_iter, tol=tol)
    res = results.summarize_run(run_output, Z0, X0, nodes, top_n=top_n)

    scenario_id = str(scenario["scenario_id"])
    scenario_dir = Path(out_dir) / scenario_id
    scenario_dir.mkdir(parents=True, exist_ok=True)

    # ---- Per-node table (node metadata + shocks + losses) ----
    node_table = res.per_node_table(nodes)
    node_table["supply_shock"] = sp
    node_table["demand_shock"] = sd
    node_table["scenario_id"] = scenario_id
    # Attach the province code from the shock matrix (aligned by node_id).
    province_lookup = scenario_matrix.set_index("node_id")["province_code"]
    node_table["province_code"] = (
        node_table["node_id"].map(province_lookup).astype("Int64")
    )
    node_table.to_csv(scenario_dir / "node_results.csv", index=False)

    # ---- Province + sector aggregations ----
    province_table = _aggregate_results(node_table, ["region_code"])
    province_table.to_csv(scenario_dir / "province_results.csv", index=False)
    sector_table = _aggregate_results(node_table, ["sector_code", "macrosector_code"])
    sector_table.to_csv(scenario_dir / "sector_results.csv", index=False)

    # ---- Flow rankings ----
    res.top_penalized_flows.to_csv(scenario_dir / "top_penalized_flows.csv", index=False)
    res.top_favored_flows.to_csv(scenario_dir / "top_favored_flows.csv", index=False)

    # ---- Flow heatmaps ----
    prov_labels, prov_groups = _group_indexer(nodes["region_code"])
    sect_labels, sect_groups = _group_indexer(nodes["sector_code"])
    _flow_heatmap_long(
        res.delta_Z, res.Z_pre, res.Z_final, prov_labels, prov_groups, "region_code"
    ).to_csv(scenario_dir / "province_flow_heatmap.csv", index=False)
    _flow_heatmap_long(
        res.delta_Z, res.Z_pre, res.Z_final, sect_labels, sect_groups, "sector_code"
    ).to_csv(scenario_dir / "sector_flow_heatmap.csv", index=False)

    # ---- Scenario summary ----
    summary = _scenario_summary(scenario, res, run_output, sp, sd, n)
    with (scenario_dir / "scenario_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    return summary


def _aggregate_results(node_table: pd.DataFrame, by: List[str]) -> pd.DataFrame:
    grouped = (
        node_table.groupby(by, as_index=False)
        .agg(
            n_nodes=("node_id", "count"),
            x_pre=("x_pre", "sum"),
            x_post=("x_post", "sum"),
            direct_loss=("direct_loss", "sum"),
            indirect_loss=("indirect_loss", "sum"),
            total_loss=("total_loss", "sum"),
            mean_supply_shock=("supply_shock", "mean"),
            max_supply_shock=("supply_shock", "max"),
        )
    )
    grouped["loss_rate"] = np.where(
        grouped["x_pre"] > 0, grouped["total_loss"] / grouped["x_pre"], 0.0
    )
    return grouped.sort_values("total_loss", ascending=False).reset_index(drop=True)


def _scenario_summary(
    scenario: pd.Series,
    res: "results.ModelResults",
    run_output: Dict[str, Any],
    sp: np.ndarray,
    sd: np.ndarray,
    n_nodes: int,
) -> Dict[str, Any]:
    totals = res.totals
    multiplier = (
        totals["total_loss"] / totals["total_direct_loss"]
        if totals["total_direct_loss"] > 0
        else None
    )
    return {
        "scenario_id": str(scenario["scenario_id"]),
        "hazard": str(scenario["hazard"]),
        "severity": str(scenario["severity"]),
        "base_interruption_days": float(scenario["base_interruption_days"]),
        "scenario_intensity_multiplier": float(
            scenario["scenario_intensity_multiplier"]
        ),
        "demand_pass_through_lambda": float(scenario["demand_pass_through_lambda"]),
        "max_supply_shock": float(scenario["max_supply_shock"]),
        "max_demand_shock": float(scenario["max_demand_shock"]),
        "n_nodes": int(n_nodes),
        "n_nodes_shocked": int((sp > 0).sum()),
        "mean_supply_shock": float(sp.mean()),
        "max_supply_shock_applied": float(sp.max()),
        "mean_demand_shock": float(sd.mean()),
        "max_demand_shock_applied": float(sd.max()),
        "converged": bool(res.convergence_status),
        "iterations": int(res.iterations),
        "total_direct_loss": float(totals["total_direct_loss"]),
        "total_indirect_loss": float(totals["total_indirect_loss"]),
        "total_loss": float(totals["total_loss"]),
        "total_x_pre": float(totals["total_x_pre"]),
        "total_x_post": float(totals["total_x_post"]),
        "loss_rate_total": (
            float(totals["total_loss"] / totals["total_x_pre"])
            if totals["total_x_pre"] > 0
            else 0.0
        ),
        "total_over_direct_multiplier": multiplier,
    }


def run_scenarios(
    scenarios: pd.DataFrame,
    shock_matrix: pd.DataFrame,
    model_inputs: Dict[str, Any],
    out_dir: Path,
    *,
    scenario_ids: Optional[List[str]] = None,
    limit_scenarios: Optional[int] = None,
    gamma: float = DEFAULT_GAMMA,
    max_iter: int = DEFAULT_MAX_ITER,
    tol: float = DEFAULT_TOL,
    top_n: int = DEFAULT_TOP_N,
) -> List[Dict[str, Any]]:
    """Run a set of scenarios and return their summary dicts."""
    selected = scenarios.copy()
    if scenario_ids:
        selected = selected[selected["scenario_id"].isin(scenario_ids)]
    if limit_scenarios is not None:
        selected = selected.head(limit_scenarios)
    if selected.empty:
        raise ValueError("No scenarios selected to run.")

    summaries: List[Dict[str, Any]] = []
    for _, scenario in selected.iterrows():
        scenario_id = str(scenario["scenario_id"])
        scenario_matrix = shock_matrix[shock_matrix["scenario_id"] == scenario_id]
        if scenario_matrix.empty:
            raise ValueError(
                f"Scenario '{scenario_id}' has no rows in the shock matrix."
            )
        print(f"[run] {scenario_id} ...", flush=True)
        summary = run_scenario(
            scenario,
            scenario_matrix,
            model_inputs,
            out_dir,
            gamma=gamma,
            max_iter=max_iter,
            tol=tol,
            top_n=top_n,
        )
        print(
            f"[done] {scenario_id}: converged={summary['converged']} "
            f"iters={summary['iterations']} total_loss={summary['total_loss']:.2f}",
            flush=True,
        )
        summaries.append(summary)
    return summaries
