"""Key performance indicators and flow-ranking helpers for model runs.

All functions are pure: they take baseline / post-shock arrays plus the
productive-node table and return NumPy arrays or pandas DataFrames. Division is
protected against zero denominators throughout.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

# Denominator floor for relative-change computations.
_REL_EPS = 1e-9


def _safe_divide(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    """Elementwise division returning 0 where the denominator is ~0."""
    numerator = np.asarray(numerator, dtype=float)
    denominator = np.asarray(denominator, dtype=float)
    out = np.zeros_like(numerator, dtype=float)
    safe = np.abs(denominator) > _REL_EPS
    out[safe] = numerator[safe] / denominator[safe]
    return out


def compute_loss_kpis(
    X0: np.ndarray, sp: np.ndarray, X_supply_final: np.ndarray
) -> Dict[str, np.ndarray]:
    """Compute the per-node loss decomposition.

    Definitions
    -----------
    ``x_pre``               = X0
    ``x_capacity_shocked``  = X0 * (1 - sp)
    ``x_post``              = X_supply_final
    ``direct_loss``         = X0 - x_capacity_shocked
    ``total_loss``          = X0 - x_post
    ``indirect_loss``       = total_loss - direct_loss
    ``loss_rate``           = total_loss / X0   (0 where X0 ~ 0)
    """
    X0 = np.asarray(X0, dtype=float).reshape(-1)
    sp = np.asarray(sp, dtype=float).reshape(-1)
    x_post = np.asarray(X_supply_final, dtype=float).reshape(-1)

    x_pre = X0
    x_capacity_shocked = X0 * (1.0 - sp)
    direct_loss = X0 - x_capacity_shocked
    total_loss = X0 - x_post
    indirect_loss = total_loss - direct_loss
    loss_rate = _safe_divide(total_loss, X0)

    return {
        "x_pre": x_pre,
        "x_capacity_shocked": x_capacity_shocked,
        "x_post": x_post,
        "direct_loss": direct_loss,
        "total_loss": total_loss,
        "indirect_loss": indirect_loss,
        "loss_rate": loss_rate,
    }


def summarize_loss_totals(kpis: Dict[str, np.ndarray]) -> Dict[str, float]:
    """Aggregate the per-node loss arrays into scalar totals."""
    return {
        "total_direct_loss": float(np.sum(kpis["direct_loss"])),
        "total_indirect_loss": float(np.sum(kpis["indirect_loss"])),
        "total_loss": float(np.sum(kpis["total_loss"])),
        "total_x_pre": float(np.sum(kpis["x_pre"])),
        "total_x_post": float(np.sum(kpis["x_post"])),
    }


def _rank_flows(
    delta_Z: np.ndarray,
    Z_pre: np.ndarray,
    Z_post: np.ndarray,
    nodes: pd.DataFrame,
    top_n: int,
    favored: bool,
) -> pd.DataFrame:
    """Rank the largest changed flows in ``delta_Z``.

    ``favored`` selects the largest positive changes (reallocated/favoured
    flows); otherwise the most negative changes (penalised flows).
    """
    delta_Z = np.asarray(delta_Z, dtype=float)
    n = delta_Z.shape[0]

    region = nodes["region_code"].to_numpy()
    sector = nodes["sector_code"].to_numpy()
    node_ids = nodes["node_id"].to_numpy()

    flat = delta_Z.ravel()
    k = min(top_n, flat.size)
    if k <= 0:
        return _empty_flow_frame()

    if favored:
        # Largest positive deltas first.
        candidate = np.argpartition(flat, -k)[-k:]
        order = candidate[np.argsort(flat[candidate])[::-1]]
    else:
        # Most negative deltas first.
        candidate = np.argpartition(flat, k - 1)[:k]
        order = candidate[np.argsort(flat[candidate])]

    origin_idx, dest_idx = np.unravel_index(order, (n, n))
    pre_value = Z_pre[origin_idx, dest_idx]
    post_value = Z_post[origin_idx, dest_idx]
    delta_value = flat[order]
    relative_change = _safe_divide(delta_value, np.abs(pre_value))

    return pd.DataFrame(
        {
            "origin_node_id": node_ids[origin_idx],
            "origin_region": region[origin_idx],
            "origin_sector": sector[origin_idx],
            "destination_node_id": node_ids[dest_idx],
            "destination_region": region[dest_idx],
            "destination_sector": sector[dest_idx],
            "delta_value": delta_value,
            "relative_change": relative_change,
            "pre_value": pre_value,
            "post_value": post_value,
        }
    ).reset_index(drop=True)


def _empty_flow_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "origin_node_id",
            "origin_region",
            "origin_sector",
            "destination_node_id",
            "destination_region",
            "destination_sector",
            "delta_value",
            "relative_change",
            "pre_value",
            "post_value",
        ]
    )


def get_top_penalized_flows(
    delta_Z: np.ndarray,
    nodes: pd.DataFrame,
    Z_pre: np.ndarray,
    Z_post: np.ndarray,
    top_n: int = 50,
) -> pd.DataFrame:
    """Return the ``top_n`` most penalised (most negative delta) flows."""
    return _rank_flows(delta_Z, Z_pre, Z_post, nodes, top_n, favored=False)


def get_top_favored_flows(
    delta_Z: np.ndarray,
    nodes: pd.DataFrame,
    Z_pre: np.ndarray,
    Z_post: np.ndarray,
    top_n: int = 50,
) -> pd.DataFrame:
    """Return the ``top_n`` most favoured (most positive delta) flows."""
    return _rank_flows(delta_Z, Z_pre, Z_post, nodes, top_n, favored=True)
