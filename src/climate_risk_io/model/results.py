"""Assemble a structured result object from a raw model run.

``summarize_run`` ties together the raw output of :meth:`IOClimateModel.run`,
the baseline inputs and the productive-node table into the full set of result
fields required by the modelling layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

import numpy as np
import pandas as pd

from . import kpi


@dataclass
class ModelResults:
    """Container for all post-processed outputs of a model run."""

    # Per-node output vectors.
    x_pre: np.ndarray
    x_capacity_shocked: np.ndarray
    x_post: np.ndarray
    direct_loss: np.ndarray
    total_loss: np.ndarray
    indirect_loss: np.ndarray
    loss_rate: np.ndarray

    # Flow matrices.
    Z_pre: np.ndarray
    Z_final: np.ndarray
    delta_Z: np.ndarray
    FD_post_final: np.ndarray

    # Convergence diagnostics.
    convergence_status: bool
    iterations: int

    # Flow rankings.
    top_penalized_flows: pd.DataFrame
    top_favored_flows: pd.DataFrame

    # Scalar totals and shock vectors.
    totals: Dict[str, float] = field(default_factory=dict)
    sd: np.ndarray = None
    sp: np.ndarray = None

    def per_node_table(self, nodes: pd.DataFrame) -> pd.DataFrame:
        """Build a per-node loss table joined with the node metadata."""
        table = nodes.copy().reset_index(drop=True)
        table["x_pre"] = self.x_pre
        table["x_capacity_shocked"] = self.x_capacity_shocked
        table["x_post"] = self.x_post
        table["direct_loss"] = self.direct_loss
        table["indirect_loss"] = self.indirect_loss
        table["total_loss"] = self.total_loss
        table["loss_rate"] = self.loss_rate
        return table


def summarize_run(
    run_output: Dict[str, Any],
    Z0: np.ndarray,
    X0: np.ndarray,
    nodes: pd.DataFrame,
    top_n: int = 50,
) -> ModelResults:
    """Post-process a raw run dict into a :class:`ModelResults`.

    Parameters
    ----------
    run_output:
        Dict returned by :meth:`IOClimateModel.run`.
    Z0, X0:
        Baseline intermediate matrix and baseline gross-output vector.
    nodes:
        Productive-node table (must contain ``node_id``, ``region_code``,
        ``sector_code``), ordered consistently with the model arrays.
    top_n:
        Number of flows to include in each ranking.
    """
    Z0 = np.asarray(Z0, dtype=float)
    X0 = np.asarray(X0, dtype=float).reshape(-1)

    sp = np.asarray(run_output["sp"], dtype=float).reshape(-1)
    sd = np.asarray(run_output["sd"], dtype=float).reshape(-1)
    Z_final = np.asarray(run_output["Z_final"], dtype=float)
    x_post = np.asarray(run_output["X_supply_final"], dtype=float).reshape(-1)

    loss = kpi.compute_loss_kpis(X0, sp, x_post)
    totals = kpi.summarize_loss_totals(loss)

    delta_Z = Z_final - Z0

    top_penalized = kpi.get_top_penalized_flows(delta_Z, nodes, Z0, Z_final, top_n)
    top_favored = kpi.get_top_favored_flows(delta_Z, nodes, Z0, Z_final, top_n)

    return ModelResults(
        x_pre=loss["x_pre"],
        x_capacity_shocked=loss["x_capacity_shocked"],
        x_post=loss["x_post"],
        direct_loss=loss["direct_loss"],
        total_loss=loss["total_loss"],
        indirect_loss=loss["indirect_loss"],
        loss_rate=loss["loss_rate"],
        Z_pre=Z0,
        Z_final=Z_final,
        delta_Z=delta_Z,
        FD_post_final=np.asarray(run_output["FD_post_final"], dtype=float).reshape(-1),
        convergence_status=bool(run_output["converged"]),
        iterations=int(run_output["iterations"]),
        top_penalized_flows=top_penalized,
        top_favored_flows=top_favored,
        totals=totals,
        sd=sd,
        sp=sp,
    )
