"""Reference one-step supply-shock propagation.

This module intentionally mirrors ``old_model_ref/propagation.py``. It contains
no CES substitution and no dynamic state update: every call receives the
baseline transaction matrix ``Z`` and the fixed exogenous capacity shock. The
outer model loop changes only final demand between calls.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np


def propagate_once(
    Z: np.ndarray,
    A: np.ndarray,
    sector_group_of: Optional[np.ndarray] = None,
    X_dem: np.ndarray = None,
    X_cap: np.ndarray = None,
    FD_post: np.ndarray = None,
    sp: np.ndarray = None,
    gamma: float = 0.5,
    *,
    globsec_of: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Run one reference propagation/reallocation step from baseline data.

    Parameters follow the old reference model. ``sector_group_of`` is the new
    name for ``globsec_of``; the legacy keyword is still accepted.

    The reference bottleneck is strict Leontief:

    1. compute producer availability ``r_i = min(1, X_cap_i / X_dem_i)``;
    2. for each buyer column ``j``, compute ``s_j = min_i r_i`` over suppliers
       with positive technical coefficient ``A[i,j]``;
    3. apply this vector row-wise as in the original implementation:
       ``Z_con[i,:] = Z[i,:] * min(s_i, 1 - sp_i)``.

    The row-wise use of a column bottleneck is deliberately preserved because
    the purpose here is to restore a clean reference baseline before changing
    the economics.
    """
    if sector_group_of is None:
        sector_group_of = globsec_of
    if sector_group_of is None:
        raise ValueError("sector_group_of (or globsec_of) must be provided.")

    Z = np.asarray(Z, dtype=float)
    A = np.asarray(A, dtype=float)
    sector_group_of = np.asarray(sector_group_of, dtype=int).reshape(-1)
    X_dem = np.asarray(X_dem, dtype=float).reshape(-1)
    X_cap = np.asarray(X_cap, dtype=float).reshape(-1)
    FD_post = np.asarray(FD_post, dtype=float).reshape(-1)
    sp = np.asarray(sp, dtype=float).reshape(-1)

    if Z.ndim != 2 or Z.shape[0] != Z.shape[1]:
        raise ValueError("Z must be a square (n x n) matrix.")
    n = Z.shape[0]
    if A.shape != (n, n):
        raise ValueError("A must have the same shape as Z (n x n).")
    if sector_group_of.shape[0] != n:
        raise ValueError("sector_group_of must have length n.")
    if (
        X_dem.shape[0] != n
        or X_cap.shape[0] != n
        or FD_post.shape[0] != n
        or sp.shape[0] != n
    ):
        raise ValueError("X_dem, X_cap, FD_post, sp must all have length n.")
    if not (0.0 <= gamma <= 1.0):
        raise ValueError("gamma must be in [0,1].")
    if (sp < 0).any() or (sp > 1).any():
        raise ValueError("sp must be within [0,1].")

    S = int(sector_group_of.max()) + 1

    # 1) Producer rationing factors.
    r = np.ones(n, dtype=float)
    mask_dem = X_dem > 0.0
    r[mask_dem] = np.minimum(1.0, X_cap[mask_dem] / X_dem[mask_dem])

    # 2) Reference strict-min bottleneck per buyer column.
    s = np.ones(n, dtype=float)
    for j in range(n):
        suppliers = A[:, j] > 0.0
        if suppliers.any():
            s[j] = r[suppliers].min()

    # 3) Preserve the old row-wise approximation exactly.
    row_factor = np.minimum(s, 1.0 - sp)
    Z_con = row_factor[:, None] * Z

    # 4-6) Required, allocated and unmet intermediate flows.
    Z_need = A * X_dem[None, :]
    Z_base = np.minimum(Z_con, Z_need)
    E = np.maximum(Z_need - Z_con, 0.0)

    # 7) Spare capacity/inventories at producer rows.
    interm_sales_con = Z_con.sum(axis=1)
    inv = np.maximum(X_cap - FD_post - interm_sales_con, 0.0)

    # 8) Aggregate inventories and unmet input demand by global sector.
    Inv_sec = np.zeros(S, dtype=float)
    Extra_sec_j = np.zeros((S, n), dtype=float)
    np.add.at(Inv_sec, sector_group_of, inv)
    np.add.at(Extra_sec_j, sector_group_of, E)
    Extra_sec = Extra_sec_j.sum(axis=1)

    # 9-10) Reallocate within the same global sector, as in the reference.
    sub = np.zeros(S, dtype=float)
    mask_sec = Extra_sec > 0.0
    sub[mask_sec] = np.minimum(1.0, Inv_sec[mask_sec] / Extra_sec[mask_sec])

    Z_new = Z_base.copy()
    for s_id in range(S):
        if Extra_sec[s_id] <= 0.0 or Inv_sec[s_id] <= 0.0:
            continue
        frac = gamma * sub[s_id]
        if frac <= 0.0:
            continue

        i_idx = np.where(sector_group_of == s_id)[0]
        inv_i = inv[i_idx]
        total_inv_i = inv_i.sum()
        if total_inv_i <= 0.0:
            continue

        inv_share = inv_i / total_inv_i
        delivered_s_j = frac * Extra_sec_j[s_id, :]
        Z_new[i_idx, :] += np.outer(inv_share, delivered_s_j)

    # 11) Local supply-side accounting output.
    X_supply_local = FD_post + Z_new.sum(axis=1)

    aux: Dict[str, Any] = {
        "X_dem": X_dem,
        "X_cap": X_cap,
        "FD_post": FD_post,
        "r": r,
        "s": s,
        "row_factor": row_factor,
        "Z_con": Z_con,
        "Z_need": Z_need,
        "Z_base": Z_base,
        "E": E,
        "inv": inv,
        "Inv_sec": Inv_sec,
        "Extra_sec": Extra_sec,
        "sub": sub,
        "tot_Z_con": float(Z_con.sum()),
        "tot_Z_need": float(Z_need.sum()),
        "tot_Z_new": float(Z_new.sum()),
        "tot_inv": float(inv.sum()),
        "tot_extra": float(E.sum()),
    }
    return Z_new, X_supply_local, aux
