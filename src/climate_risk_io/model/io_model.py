"""Reference region-sector physical-risk propagation model.

This implementation is intentionally close to ``old_model_ref/model.py``. It
keeps the project-specific improvements that are not economic changes
(validation, vector-only shocks, and solving ``(I - A) X = FD`` instead of
materialising a dense Leontief inverse by default), but removes the extra model
variants that had been added while experimenting.

Important iteration rule
------------------------
The outer loop is **not** a dynamic simulation. Iteration ``k+1`` does not start
from ``Z_new`` or output produced by iteration ``k``. Every propagation step
starts from the same baseline objects:

* ``self.Z0``: baseline intermediate transaction matrix;
* ``self.A0``: baseline technical coefficients;
* ``X_cap0 = X0 * (1 - sp)``: fixed exogenous supply capacity.

Only ``FD_post`` changes between iterations. The loop searches for a post-shock
final-demand vector that is coherent with the fixed exogenous supply shock under
the reference global-technology feasibility rule.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

import numpy as np
from scipy.linalg import lu_factor, lu_solve

from .propagation import propagate_once


class _DemandSolver:
    """Reusable solver for ``(I - A) X = FD``."""

    def __init__(self, A: np.ndarray) -> None:
        n = A.shape[0]
        self._ImA = np.eye(n) - A
        self._lu = None

    def solve(self, fd: np.ndarray) -> np.ndarray:
        if self._lu is None:
            self._lu = lu_factor(self._ImA)
        return lu_solve(self._lu, fd)


class IOClimateModel:
    """Multi-region, multi-sector reference propagation model."""

    def __init__(
        self,
        Z0: np.ndarray,
        FD0: np.ndarray,
        X0: np.ndarray,
        sector_group_of: np.ndarray,
        A0: Optional[np.ndarray] = None,
        L0: Optional[np.ndarray] = None,
        node_labels: Optional[Sequence[str]] = None,
    ) -> None:
        Z0 = np.asarray(Z0, dtype=float)
        FD0 = np.asarray(FD0, dtype=float).reshape(-1)
        X0 = np.asarray(X0, dtype=float).reshape(-1)
        sector_group_of = np.asarray(sector_group_of, dtype=int).reshape(-1)

        if Z0.ndim != 2 or Z0.shape[0] != Z0.shape[1]:
            raise ValueError("Z0 must be a square (n x n) matrix.")
        n = Z0.shape[0]
        if FD0.shape[0] != n:
            raise ValueError(f"FD0 must have length n = {n}, got {FD0.shape[0]}.")
        if X0.shape[0] != n:
            raise ValueError(f"X0 must have length n = {n}, got {X0.shape[0]}.")
        if sector_group_of.shape[0] != n:
            raise ValueError(
                f"sector_group_of must have length n = {n}, "
                f"got {sector_group_of.shape[0]}."
            )
        if not np.isfinite(Z0).all():
            raise ValueError("Z0 contains non-finite values.")
        if not np.isfinite(FD0).all():
            raise ValueError("FD0 contains non-finite values.")
        if not np.isfinite(X0).all():
            raise ValueError("X0 contains non-finite values.")
        if (sector_group_of < 0).any():
            raise ValueError("sector_group_of must contain non-negative ids.")

        self.n = n
        self.sector_group_of = sector_group_of
        self.S_glob = int(sector_group_of.max()) + 1
        self.node_labels = (
            [f"node_{i}" for i in range(n)]
            if node_labels is None
            else list(node_labels)
        )
        if len(self.node_labels) != n:
            raise ValueError("node_labels must have length n.")

        self.Z0 = Z0
        self.FD0 = FD0
        self.X0 = X0

        if A0 is None:
            A0 = self._compute_technical_coefficients(Z0, X0)
        else:
            A0 = np.asarray(A0, dtype=float)
            if A0.shape != (n, n):
                raise ValueError("A0 must have the same shape as Z0 (n x n).")
        self.A0 = A0

        self.L0 = None
        if L0 is not None:
            L0 = np.asarray(L0, dtype=float)
            if L0.shape != (n, n):
                raise ValueError("L0 must have the same shape as Z0 (n x n).")
            self.L0 = L0
        self._solver = _DemandSolver(self.A0)

        self.ZG0 = self._aggregate_to_sector_groups(self.Z0)
        self.A_G = self._compute_technical_coefficients(self.ZG0, self.X0)

    def run(
        self,
        sd: np.ndarray,
        sp: np.ndarray,
        *,
        gamma: float = 0.5,
        max_iter: int = 50,
        tol: float = 1e-6,
        return_history: bool = False,
    ) -> Dict[str, Any]:
        """Run the reference model in vector mode.

        ``sd`` and ``sp`` are demand and supply shock vectors in ``[0, 1]``.
        The supply shock fixes capacity for the whole run. The initial demand
        shock sets ``FD_post``; subsequent iterations update only ``FD_post``.

        Each iteration deliberately calls ``propagate_once`` with ``self.Z0`` and
        ``self.A0``. This is the central reference-model rule: propagated flows
        from one iteration are diagnostics for that demand guess, not the state
        for the next iteration.
        """
        if not (0.0 <= gamma <= 1.0):
            raise ValueError("gamma must be in [0,1].")
        if max_iter <= 0:
            raise ValueError("max_iter must be positive.")
        if tol <= 0:
            raise ValueError("tol must be positive.")

        sd = np.asarray(sd, dtype=float).reshape(-1)
        sp = np.asarray(sp, dtype=float).reshape(-1)
        if sd.shape[0] != self.n or sp.shape[0] != self.n:
            raise ValueError(f"sd and sp must both have length n = {self.n}.")
        if (sd < 0).any() or (sd > 1).any():
            raise ValueError("sd must be within [0,1].")
        if (sp < 0).any() or (sp > 1).any():
            raise ValueError("sp must be within [0,1].")

        X_cap0 = self.X0 * (1.0 - sp)
        FD_post = self.FD0 * (1.0 - sd)

        eps = 1e-12
        converged = False

        FD_post_hist = []
        FD_implied_hist = []
        X_supply_hist = []
        demand_update_gap_hist = []

        Z_new = np.zeros_like(self.Z0)
        X_supply = np.zeros(self.n, dtype=float)
        X_supply_local = np.zeros(self.n, dtype=float)
        X_supply_global = np.zeros(self.n, dtype=float)
        FD_implied = np.zeros(self.n, dtype=float)
        aux_last: Dict[str, Any] = {}
        demand_update_gap = np.inf
        it = 0

        for it in range(1, max_iter + 1):
            # 1) Demand-only gross output for the current demand guess.
            X_dem = self._demand_output(FD_post)

            # 2) Reference propagation from the immutable baseline. Do not pass
            #    last iteration's Z_new or X_supply back into this step.
            Z_new, X_supply_local, aux_last = propagate_once(
                Z=self.Z0,
                A=self.A0,
                sector_group_of=self.sector_group_of,
                X_dem=X_dem,
                X_cap=X_cap0,
                FD_post=FD_post,
                sp=sp,
                gamma=gamma,
            )

            # 3) Strict global-technology feasibility, exactly as in the old
            #    reference: for each buyer j, output is bounded by the scarcest
            #    global-sector input relative to fixed baseline A_G.
            ZG_new = self._aggregate_to_sector_groups(Z_new)
            X_supply_global = self._global_feasibility_cap(ZG_new, X_supply_local)
            X_supply = np.minimum(X_supply_local, X_supply_global)

            # 4) Implied final demand under the feasible output and current
            #    reallocated intermediate matrix.
            FD_implied = np.maximum(X_supply - Z_new.sum(axis=1), 0.0)

            if return_history:
                FD_post_hist.append(FD_post.copy())
                FD_implied_hist.append(FD_implied.copy())
                X_supply_hist.append(X_supply.copy())

            # 5) Monotone demand update. The next iteration restarts from the
            #    baseline Z0/sp and uses only this updated demand vector.
            FD_post_next = np.minimum(FD_post, FD_implied)
            denom = np.linalg.norm(FD_post, ord=1) + eps
            demand_update_gap = (
                np.linalg.norm(FD_post_next - FD_post, ord=1) / denom
            )
            demand_update_gap_hist.append(float(demand_update_gap))

            if demand_update_gap < tol:
                converged = True
                FD_post = FD_post_next
                break
            FD_post = FD_post_next

        result: Dict[str, Any] = {
            "converged": converged,
            "iterations": it,
            "Z_final": Z_new,
            "X_supply_final": X_supply,
            "X_supply_local_last": X_supply_local,
            "X_supply_global_last": X_supply_global,
            "FD_post_final": FD_post,
            "FD_implied_final": FD_implied,
            "sd": sd,
            "sp": sp,
            "aux_last": aux_last,
            "demand_update_gap_last": float(demand_update_gap),
            "model_variant": "reference_strict_min",
        }
        if return_history:
            result["FD_post_history"] = FD_post_hist
            result["FD_implied_history"] = FD_implied_hist
            result["X_supply_history"] = X_supply_hist
            result["demand_update_gap_history"] = demand_update_gap_hist
        return result

    def _demand_output(self, fd: np.ndarray) -> np.ndarray:
        """Demand-only gross output: ``L0 @ fd`` if supplied, else LU solve."""
        if self.L0 is not None:
            return self.L0 @ fd
        return self._solver.solve(fd)

    def _global_feasibility_cap(
        self, ZG_new: np.ndarray, X_supply_local: np.ndarray
    ) -> np.ndarray:
        """Strict reference cap ``min_s ZG_new[s,j] / A_G[s,j]``."""
        mask = self.A_G > 0.0
        with np.errstate(divide="ignore", invalid="ignore"):
            caps = np.where(mask, ZG_new / np.where(mask, self.A_G, 1.0), np.inf)
        X_supply_global = caps.min(axis=0)
        no_inputs = ~mask.any(axis=0)
        X_supply_global[no_inputs] = X_supply_local[no_inputs]
        return X_supply_global

    @staticmethod
    def _compute_technical_coefficients(Z: np.ndarray, X: np.ndarray) -> np.ndarray:
        """Compute ``A[i, j] = Z[i, j] / X[j]`` with zero-output protection."""
        Z = np.asarray(Z, dtype=float)
        X = np.asarray(X, dtype=float).reshape(-1)
        if Z.shape[1] != X.shape[0]:
            raise ValueError("X length must match Z.shape[1] (columns).")
        denom = X.copy()
        denom[denom == 0.0] = np.nan
        A = Z / denom[None, :]
        return np.nan_to_num(A, nan=0.0)

    def _aggregate_to_sector_groups(self, Z: np.ndarray) -> np.ndarray:
        """Sum rows of ``Z`` by sector group: (n, n) -> (S, n)."""
        Z = np.asarray(Z, dtype=float)
        if Z.shape != (self.n, self.n):
            raise ValueError("Z must be (n x n) for sector-group aggregation.")
        ZG = np.zeros((self.S_glob, self.n), dtype=float)
        np.add.at(ZG, self.sector_group_of, Z)
        return ZG
