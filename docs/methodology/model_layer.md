# Modelling layer

The modelling layer estimates **business interruption** â€” lost value of
production by province Ã— sector â€” caused by climate-related physical-risk supply
shocks. It is an input-output propagation model that runs on the productive
block of the multi-regional SAM. It does **not** estimate physical asset damage.

Package: `src/climate_risk_io/model/`

```text
label_parser.py   parse + classify account labels
input_builder.py  SAM -> model inputs (Z0, FD0, X0, VA0, IMP0, sector groups)
io_model.py       IOClimateModel: the iterative propagation model
propagation.py    propagate_once: one rationing + reallocation step
kpi.py            loss decomposition + top flow rankings
results.py        assemble a ModelResults object from a raw run
```

## 1. Model inputs

From the full SAM the builder slices (see
[sam_account_structure.md](sam_account_structure.md)):

```text
Z0[i, j] = SAM[productive row i, productive column j]
FD0[i]   = sum over final-demand columns of SAM[productive row i, .]
VA0[k, j]= SAM[value-added row k, productive column j]
IMP0[m,j]= SAM[external/import row m, productive column j]
X0[i]    = row_sum(Z0[i, :]) + FD0[i]
```

Node ordering is deterministic: `region_code` ascending, then `sector_code`
ascending. Every array and CSV shares this order. `globsec_of[k]` is the
sector-group id of productive node `k` (all regional nodes of a sector share an
id); `sector_mapping.csv` maps `sector_group_id -> (sector_code, macrosector_code)`.

### Accounting diagnostic

The builder reports a row-vs-column reconciliation:

```text
intermediate_inputs_by_column[j] = sum_i Z0[i, j]
value_added_by_column[j]         = sum_k VA0[k, j]
import_inputs_by_column[j]       = sum_m IMP0[m, j]
X0_column_check[j]               = intermediate_inputs_by_column[j]
                                   + value_added_by_column[j]
                                   + import_inputs_by_column[j]
row_output_vs_column_output_gap  = X0 - X0_column_check
```

Row and column output are **not** forced equal. The gap and the maximum relative
error are reported; a large gap raises a warning. `ROW` is role-specific: as a
column it remains final demand, while as a row into productive columns it is an
external/import input included in `IMP0`. The report also keeps a `va_only`
diagnostic to show the gap that would appear if ROW input rows were excluded.

## 2. Propagation model

`IOClimateModel.run(sd, sp, gamma, max_iter, tol)` â€” **vector mode only**. The
caller supplies the demand shock `sd` and supply shock `sp` (both length
`n_productive`, in `[0, 1]`). Scenario targeting is intentionally outside the
model.

Fixed quantities:

```text
A0[i, j] = Z0[i, j] / X0[j]                  baseline technical coefficients
A_G[s, j]= (sum over group-s rows of Z0)[j] / X0[j]   fixed aggregated technology
X_cap0   = X0 * (1 - sp)                     capacity after the supply shock
FD_post0 = FD0 * (1 - sd)                    initial post-shock final demand
```

Outer loop (on demand only), for `k = 1..max_iter`:

1. **Demand-only output**: solve `(I - A0) X_dem = FD_post`. This replaces the
   dense Leontief inverse `L0 @ FD_post`; the factorisation of `(I - A0)` is
   computed once (LU) and reused. A precomputed `L0` is used only if explicitly
   passed to the constructor.
2. **Propagate + reallocate** (`propagate_once`): supplier rationing, the
   reference strict-min bottleneck, constrained vs needed flows,
   within-sector-group inventory
   reallocation. Returns `Z_new` and a local supply output.
3. **Global technology cap**: `X_supply = min(X_supply_local, X_supply_global)`.
   The global cap is the reference fixed-proportions rule,
   `X_supply_global[j] = min_s ZG_new[s,j] / A_G[s,j]`.
4. **Implied final demand**: `FD_implied = max(X_supply - row_sum(Z_new), 0)`.
5. **Monotone demand update**: `FD_post <- min(FD_post, FD_implied)`.

Convergence: `||FD_post_next - FD_post||_1 / ||FD_post||_1 < tol`.

Every iteration restarts from `Z0`, `A0` and the fixed `X_cap0`; only
`FD_post` changes between iterations. `Z_new` is a diagnostic/result for the
current demand guess, not the next iteration's starting state.

### `propagate_once` (one step) - reference strict-min bottleneck

```text
r_i        = min(1, X_cap_i / X_dem_i)                 supplier availability
s_j        = min_i r_i where A[i,j] > 0                strict buyer bottleneck
row_factor_i = min(s_i, 1 - sp_i)                     reference row-wise approximation
Z_con[i,:] = Z[i,:] * row_factor_i
Z_need     = A * X_dem[None, :]                        needed flows
Z_base     = min(Z_con, Z_need)
E          = max(Z_need - Z_con, 0)                   extra (unmet) demand
inv_i      = max(X_cap_i - FD_post_i - row_sum(Z_con)_i, 0)   inventories
sub_s      = min(1, Inv_sec_s / Extra_sec_s)
Z_new      = Z_base + gamma * sub_s * (extra demand distributed by inventory share)
X_supply_local = FD_post + row_sum(Z_new)
```

The argument named `globsec_of` in the reference code is renamed
`sector_group_of` (the legacy keyword is still accepted as an alias).

## 3. KPIs and results

`results.summarize_run` produces:

```text
x_pre = X0
x_capacity_shocked = X0 * (1 - sp)
x_post = X_supply_final
direct_loss   = X0 - x_capacity_shocked
total_loss    = X0 - x_post
indirect_loss = total_loss - direct_loss
loss_rate     = total_loss / X0        (0 where X0 ~ 0)
Z_pre, Z_final, delta_Z = Z_final - Z0, FD_post_final
convergence_status, iterations
top_penalized_flows, top_favored_flows
```

Flow rankings (`kpi.get_top_penalized_flows` / `get_top_favored_flows`) return,
per ranked flow: origin/destination node id, region and sector; `delta_value`,
`relative_change` (safe against tiny denominators), `pre_value`, `post_value`.

## 4. Assumptions

1. Productive accounts are macrosector `{A, I, S}`.
2. Final-demand columns are macrosector `{HH, CF, G, R}`.
3. Value-added accounts are macrosector `{L, K, T}`.
4. `ROW` / macrosector `R` is final demand as a column and an external/import
   input as a row into productive columns.
5. `X0 = row_sum(Z0) + FD0`.
6. The propagation model operates only on productive accounts.
7. The input bottleneck is the reference strict minimum; the aggregated
   global-feasibility cap is the reference strict fixed-proportions rule.
8. Demand and supply shocks are passed as explicit vectors.

## 5. Indirect-impact propagation: history and current state

**Current restored baseline.** The implementation has been simplified back to
the old reference logic. This is useful as a transparent baseline, but it also
reproduces the reference model's main weakness on the dense Italian MRIO:
strict-min bottlenecks can create very large indirect impacts.

Diagnosis:

* **`X_dem` was not the cause.** Solving `(I - A0) X = FD` is numerically
  identical (~1e-11) to the old `L0 @ FD`; the port reproduced the reference to ~1e-14.
* **The strict-min Leontief bottlenecks are the cause of large impacts.** Both the local
  bottleneck `s_j = min_{i: A_ij>0} r_i` and the global-feasibility cap
  `X_glob[j] = min_s ZG[s,j]/A_G[s,j]` are strict minima. In a dense MRIO a
  near-universal trivial supplier (`A01` sells to 298/298 sectors, median input
  share â‰ˆ 0) drags both down for every sector, so one shocked node throttled the
  whole economy; the global cap + monotone `FD_implied` feedback amplified
  24x â†’ 357x over the outer iterations.

The restored baseline intentionally keeps these strict-min mechanics so future
changes can be measured against the reference rather than mixed with earlier
experiments.

## 6. Alignment with the paper and toy workbook

The uploaded paper describes a ten-step algorithm:

```text
FD_post = FD0 * (1 - demand shock)
X_cap   = X0  * (1 - production shock)
X_dem   = L0 @ FD_post
r_i     = min(1, X_cap_i / X_dem_i)
s_j     = min_i r_i over positive A[i,j]
Z_cons  = Z0 scaled by the strongest production/input constraint
Z_need  = A0 * X_dem
E       = max(Z_need - Z_cons, 0)
inv_i   = max(X_cap_i - FD_post_i - row_sum(Z_cons)_i, 0)
Z_new   = min(Z_cons, Z_need) + gamma reallocation within the same global sector
X_new   = min_s ZG_new[s,j] / A_G[s,j]
```

The current `propagate_once` implements these steps and intentionally keeps the
same row-wise `Z_cons` approximation found in the reference workbook/code. This
row-wise use of `s` is a modelling approximation, not a Python bug.

The paper's last step says to form a new aggregate demand vector equivalent to
the feasible output and iterate again from equation (1). The code follows that
interpretation directly: each iteration restarts from `Z0`, `A0` and fixed
`X_cap0`, while carrying forward only the updated `FD_post` vector.

The workbook `ECB_IO_physicalrisk.xlsx` confirms the core implementation:
`scripts/check_paper_toy_alignment.py` reproduces the first propagation pass
against the `IO_sub_model` sheet to floating-point precision for `X_dem`, `r`,
`s`, `row_factor`, inventories, `Z_new`, the global output cap and the first
demand update. A second one-step run from the workbook `t+1` demand guess also
matches the `t+1` `Z_new` matrix.

One workbook caveat remains: from `t+2` onward the spreadsheet accumulates
new demand-shock percentages relative to the current `FD_post`. The code carries
the post-shock final-demand vector itself, which is closer to the paper wording
and avoids ambiguity about shock denominators. This affects later workbook tabs'
reported demand-shock percentages, not the one-step propagation equations.

## 7. Performance note

The full Italian productive block is ~6462 nodes. The demand solve LU-factorises
a dense `(I - A0)` of that size and `propagate_once` allocates several dense
`n Ã— n` arrays per iteration. This is feasible but heavy; the smoke test runs on
a subset of regions by default (`--full` runs the whole block). Persisting the
dense Leontief inverse is intentionally **not** done by default.
