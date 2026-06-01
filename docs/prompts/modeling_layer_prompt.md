# Codex / Claude Code Prompt — Create the Modelling Layer for `Supply-shock-MRIO-model`

You are working on the GitHub repository:

```text
Supply-shock-MRIO-model
```

The repository already contains:

- climate exposure data preparation, including validated heatwave exposure indicators;
- flood and landslide exposure data;
- SAM data ingestion/materialisation from Databricks;
- a working Python 3.12 environment in `.venv`;
- a SAM table structure based on labelled accounts;
- an old model implementation that will be placed in the repository root under:

```text
old_model_ref/
```

The old scripts in `old_model_ref/` should be studied and used as methodological reference. Do **not** blindly copy them. Adapt them cleanly to the current repository structure, naming conventions, SAM format, and MVP requirements.

The old model logic implements an input-output climate shock propagation model with:

- supply shock vector;
- demand shock vector;
- constrained production capacity;
- Leontief demand-side propagation;
- intermediate-input rationing;
- within-sector reallocation;
- iterative final-demand adjustment until convergence.

The current task is to build the **modelling layer** of the MVP.

Do not build the web app yet. Do not introduce FastAPI, Next.js, Docker, Redis, Celery, databases, or cloud deployment.

Keep the implementation readable, testable, and maintainable.

---

## 1. Overall project purpose

The project is an MVP analytical engine to estimate the impact of climate-related physical risk shocks on Italian economic sectors at provincial level.

The final application will estimate **business interruption effects**, not physical asset damage.

Main model output:

```text
lost value of production
```

by:

```text
province × sector
```

and eventually:

```text
scenario × hazard × province × sector
```

The model must also return changes in the economic flow structure, including:

- post-shock intermediate transaction matrix;
- delta between pre-shock and post-shock flows;
- most penalised flows;
- most favoured/reallocated flows.

---

## 2. Existing data layers

The project already has:

```text
data/processed/climate/
```

with heatwave, flood, and landslide exposure data.

The SAM data have also been collected/materialised. The current SAM solution works, even if it may be improved later. Do not redesign the SAM ingestion pipeline now unless absolutely required for the modelling layer.

The modelling layer should consume existing SAM artifacts and produce clean model-ready inputs.

---

## 3. SAM source structure and naming convention

The SAM source table is:

```text
ml.sam.mrsam_downscaled_y
```

It is in long format.

Relevant table columns:

```text
matrix_id
region_orig
ind_ava
region_dest
ind_use
value
time_period
row_label
col_label
```

The following columns may exist but should not be needed for the modelling layer:

```text
share
materialized_at
mlflow_experiment_name
mlflow_run_id
```

Column meaning:

```text
region_orig = row region / seller/origin account region
ind_ava     = row sector / origin account sector
region_dest = column region / buyer/destination account region
ind_use     = column sector / destination account sector
value       = SAM cell value
row_label   = full row account label
col_label   = full column account label
```

Matrix convention:

```text
row    = seller / supplier / origin / producing account
column = buyer / destination / using account
value  = monetary flow paid by the column account to the row account; economically, it records the value supplied by the row account and purchased/used by the column account
```

Therefore, in the productive transaction block:

```text
Z[i, j] = monetary payment flow from buyer productive node j to seller productive node i; equivalently, the value of goods/services supplied by seller i and purchased/used by buyer j
```

Important interpretation:

```text
The physical/economic supply relation is row i -> column j.
The monetary payment direction is column j -> row i.
The matrix orientation remains row = seller/supplier and column = buyer/user.
```

This is the standard IO accounting orientation: `Z[i, j]` is the value of inputs supplied by account `i` and purchased by account `j`.


---

## 4. SAM labels

Each row and column account has a full label:

```text
region__sector__macrosector
```

with **double underscore** as separator.

Examples:

```text
ITC11__A01__A
ITC11__C10__I
ITC11__M69__S
EU-ITA__LAB__L
EU-ITA__CAP__K
EU-ITA__TAX__T
EU-ITA__HH__HH
EU-ITA__CF__CF
EU-ITA__GOV__G
EU-ITA__ROW__R
```

The label parser must split labels into:

```text
region_code
sector_code
macrosector_code
```

using `__` as separator.

If a label does not split into exactly three parts, fail with a clear validation error.

---

## 5. Account classification

### Productive accounts

Productive accounts are those with macrosector:

```text
A
I
S
```

Meaning:

```text
A = agriculture
I = industry
S = services
```

Productive sector labels are NACE-like alphanumeric codes such as:

```text
A01
A02
C10
M69
...
```

Productive accounts have region-specific NUTS/provincial region codes.

### Institutional / value-added accounts

Value-added / primary-input accounts:

```text
EU-ITA__LAB__L
EU-ITA__CAP__K
EU-ITA__TAX__T
```

Classification:

```text
LAB / L = labour
CAP / K = capital
TAX / T = indirect taxes
```

These are value-added rows when crossed with productive columns.

### Institutional / final-demand accounts

Final-demand accounts:

```text
EU-ITA__HH__HH
EU-ITA__CF__CF
EU-ITA__GOV__G
EU-ITA__ROW__R
```

Classification:

```text
HH  / HH = households
CF  / CF = capital formation
GOV / G  = government
ROW / R  = rest of world
```

`ROW` with macrosector `R` must be treated as part of final demand.

### Model masks

The model-input builder must create clear masks:

```text
is_productive_account
is_final_demand_account
is_value_added_account
is_institutional_account
```

Definitions:

```text
productive macrosectors   = {A, I, S}
final demand macrosectors = {HH, CF, G, R}
value added macrosectors  = {L, K, T}
```

Use macrosector codes from parsed labels as the primary classification source.

---

## 6. SAM-to-model transformation

The propagation model must run only on the **productive block**.

Given the full SAM:

```text
Z0  = productive rows × productive columns
FD0 = productive rows × final-demand columns, summed by productive row
VA0 = value-added rows × productive columns
X0  = row output of productive accounts
```

Specifically:

```text
FD0[i] = sum over final-demand columns j of SAM[productive row i, final-demand column j]
```

```text
Z0[i, j] = SAM[productive row i, productive column j]
```

```text
X0[i] = row_sum(Z0[i, :]) + FD0[i]
```

Also compute column-side production accounting diagnostics:

```text
intermediate_inputs_by_column[j] = sum over productive rows i of Z0[i, j]
value_added_by_column[j] = sum over value-added rows k of SAM[value-added row k, productive column j]
X0_column_check[j] = intermediate_inputs_by_column[j] + value_added_by_column[j]
```

Then report:

```text
row_output_vs_column_output_gap = X0 - X0_column_check
```

Do not force equality. Report the gap and relative error. If the gap is large, warn clearly.

---

## 7. Model-ready outputs

Create a dedicated model-input folder:

```text
data/processed/model_inputs/
```

Required outputs:

```text
data/processed/model_inputs/productive_nodes.csv
data/processed/model_inputs/account_nodes.csv
data/processed/model_inputs/Z0.npy
data/processed/model_inputs/FD0.npy
data/processed/model_inputs/X0.npy
data/processed/model_inputs/VA0.npy
data/processed/model_inputs/globsec_of.npy
data/processed/model_inputs/sector_mapping.csv
data/processed/model_inputs/model_input_report.json
```

Optional outputs:

```text
data/processed/model_inputs/A0.npy
```

Do **not** compute and store the dense Leontief inverse by default. For the full matrix size, explicitly inverting `(I - A)` may be expensive and numerically fragile.

Instead, the model class should solve:

```text
(I - A) X = FD
```

when demand-side output is needed.

Only add optional Leontief inverse caching if explicitly enabled.

---

## 8. Node ordering

The productive node ordering must be deterministic and consistent across all arrays.

Use this ordering:

```text
region_code ascending
sector_code ascending
```

`productive_nodes.csv` should contain:

```text
node_id
region_code
sector_code
macrosector_code
node_label
```

where:

```text
node_label = region_code + "__" + sector_code + "__" + macrosector_code
```

`globsec_of.npy` maps each productive node to its sector group ID.

Sector group means the productive sector code, not the macrosector.

Example:

```text
All regional A01 nodes share the same sector group.
All regional C10 nodes share the same sector group.
```

Create `sector_mapping.csv`:

```text
sector_group_id
sector_code
macrosector_code
```

The `sector_group_id` must be an integer starting from 0.

---

## 9. Modelling package structure

Create the modelling package:

```text
src/climate_risk_io/model/
  __init__.py
  label_parser.py
  input_builder.py
  io_model.py
  propagation.py
  kpi.py
  results.py
```

Use the old scripts in:

```text
old_model_ref/
```

as reference for `io_model.py` and `propagation.py`.

Do not import directly from `old_model_ref/`.

---

## 10. label_parser.py

Implement:

```python
parse_account_label(label: str) -> dict
classify_account(parsed_label: dict) -> str
```

`parse_account_label` should return:

```python
{
    "region_code": ...,
    "sector_code": ...,
    "macrosector_code": ...,
}
```

`classify_account` should return one of:

```text
productive
final_demand
value_added
other_institutional
unknown
```

Fail clearly for malformed labels.

---

## 11. input_builder.py

Implement functions to build model inputs from existing SAM artifacts.

Expected functions:

```python
load_full_sam_artifact(...)
build_account_metadata(...)
build_productive_block(...)
build_final_demand_vector(...)
build_value_added_block(...)
build_output_vector(...)
build_globsec_mapping(...)
write_model_inputs(...)
build_model_inputs(...)
```

The builder should be robust to whether the SAM artifact is currently stored as:

- dense `.npy` full matrix plus `nodes.csv`;
- or another working local artifact already present in the repository.

Do not redesign SAM ingestion. Consume the current working SAM output.

If the existing SAM output is missing full account labels required to distinguish productive/final demand/value added accounts, fail with a clear error explaining that `row_label` and `col_label` or equivalent account labels are required.

---

## 12. io_model.py

Adapt the old `IOClimateModel` into the new package.

Changes required:

1. Rename language from country-sector to region-sector / province-sector.
2. Remove dependency on `make_shock_vectors`.
3. Use vector mode only for now:

```python
results = model.run(sd=sd, sp=sp, gamma=0.5)
```

where:

```text
sd = demand shock vector, length n_productive
sp = supply shock vector, length n_productive
```

4. Preserve the old propagation logic unless a change is required for correctness.
5. Do not hard-code scenario targeting inside the model.
6. Add clear validation for `Z0`, `FD0`, `X0`, and `globsec_of`.
7. Avoid computing dense Leontief inverse by default.

Instead of:

```python
X_dem = L0 @ FD_post
```

prefer:

```python
X_dem = solve((I - A0), FD_post)
```

For performance, create a reusable solver object if practical. Keep it simple.

8. Keep optional support for a precomputed `L0` only if explicitly provided.

---

## 13. propagation.py

Port the old `propagate_once` logic.

Preserve the core logic:

- rationing factors;
- bottleneck constraints;
- constrained flows;
- required flows;
- unmet intermediate demand;
- inventories;
- within-sector reallocation;
- local supply-side accounting output;
- diagnostics dictionary.

Use naming consistent with the new model:

```text
sector_group_of
```

instead of:

```text
globsec_of
```

unless keeping `globsec_of` avoids excessive changes. If keeping the old name, document that it means sector group ID.

Do not change the row-wise approximation unless explicitly instructed. The old implementation notes that bottleneck constraints are defined per using sector but applied row-wise as an approximation. Preserve this behaviour and document it.

---

## 14. kpi.py and results.py

Create post-processing utilities.

Required outputs from a model run:

```text
x_pre
x_capacity_shocked
x_post
direct_loss
total_loss
indirect_loss
loss_rate
Z_pre
Z_final
delta_Z
FD_post_final
convergence_status
iterations
top_penalized_flows
top_favored_flows
```

Definitions:

```text
x_pre = X0
x_capacity_shocked = X0 * (1 - sp)
x_post = X_supply_final
direct_loss = X0 - x_capacity_shocked
total_loss = X0 - x_post
indirect_loss = total_loss - direct_loss
loss_rate = total_loss / X0
delta_Z = Z_final - Z0
```

Protect against division by zero.

Create top-flow ranking helpers:

```python
get_top_penalized_flows(delta_Z, nodes, top_n=50)
get_top_favored_flows(delta_Z, nodes, top_n=50)
```

Flow ranking output should include:

```text
origin_node_id
origin_region
origin_sector
destination_node_id
destination_region
destination_sector
delta_value
relative_change
pre_value
post_value
```

Handle very small denominators safely for `relative_change`.

---

## 15. Scripts

Create these scripts:

```text
scripts/build_model_inputs_from_sam.py
scripts/run_model_smoke_test.py
scripts/test_model_layer.py
```

### build_model_inputs_from_sam.py

This script should:

- load current SAM artifact;
- parse account labels;
- classify accounts;
- build `Z0`, `FD0`, `X0`, `VA0`, `globsec_of`;
- write model-ready files to `data/processed/model_inputs/`;
- write `model_input_report.json`.

### run_model_smoke_test.py

This script should:

- load model-ready inputs;
- create a small artificial shock vector;
- run the model on a small subset if full run is too heavy;
- print convergence status;
- print total direct, indirect, and total loss;
- print top penalized/favored flows.

### test_model_layer.py

This script should run non-Databricks tests only.

It should validate:

- account-label parser;
- account classification;
- productive/final-demand/value-added masks;
- model input files exist after build;
- array dimensions are consistent;
- `Z0`, `FD0`, `X0`, `globsec_of` align;
- `X0 = row_sum(Z0) + FD0` within tolerance;
- model runs on a synthetic small SAM;
- KPI functions return expected columns.

Do not require Databricks authentication.

---

## 16. Synthetic test

Create a small synthetic SAM inside the test code.

It should include:

- at least two productive regions;
- at least two productive sectors;
- final demand accounts: HH, CF, GOV, ROW;
- value-added accounts: LAB, CAP, TAX.

Use synthetic labels such as:

```text
IT001__A01__A
IT001__C10__I
IT002__A01__A
IT002__C10__I
EU-ITA__LAB__L
EU-ITA__CAP__K
EU-ITA__TAX__T
EU-ITA__HH__HH
EU-ITA__CF__CF
EU-ITA__GOV__G
EU-ITA__ROW__R
```

Validate that:

```text
Z0 = productive × productive
FD0 = productive rows × final demand columns
VA0 = value-added rows × productive columns
X0 = row_sum(Z0) + FD0
```

---

## 17. Repository polishing

Take this opportunity to polish the repository structure, but do not over-refactor.

Allowed:

- create missing `__init__.py` files;
- create `docs/` if useful;
- update README;
- move prompt/reference markdown files into `docs/prompts/`;
- move methodology notes into `docs/methodology/`;
- improve script names if needed;
- ensure generated files are ignored;
- ensure tests are easy to run.

Do not:

- delete raw data;
- delete processed climate data;
- change heatwave methodology;
- change SAM ingestion unless necessary;
- change Databricks authentication;
- introduce app/backend/frontend infrastructure;
- add complex dependency managers.

Recommended docs:

```text
docs/methodology/model_layer.md
docs/methodology/sam_account_structure.md
docs/prompts/
```

Update README with a short “Modelling layer” section explaining:

- SAM account classification;
- model input construction;
- propagation model;
- how to build model inputs;
- how to run the smoke test;
- how to run model tests.

---

## 18. .gitignore

Ensure generated model artifacts are ignored:

```gitignore
data/processed/model_inputs/
*.npy
data/**/*.json
```

Do not ignore source code, scripts, README, requirements, or docs.

---

## 19. Commands to document

Document these commands:

```powershell
.\.venv\Scripts\python.exe scripts\build_model_inputs_from_sam.py

.\.venv\Scripts\python.exe scripts\run_model_smoke_test.py

.\.venv\Scripts\python.exe scripts\test_model_layer.py
```

Also document the existing global project test:

```powershell
.\.venv\Scripts\python.exe test_project_setup.py
```

---

## 20. Important constraints

- Use `old_model_ref/` only as reference.
- Do not import from `old_model_ref/`.
- Do not change heatwave scripts.
- Do not delete data.
- Do not hardcode secrets.
- Do not require Databricks for model-layer tests.
- Do not build the frontend/backend app yet.
- Keep the code explicit and understandable.

---

## 21. Final response required

After implementation, summarize:

- files created;
- files modified;
- old model logic ported;
- SAM account parsing/classification implemented;
- model input builder implemented;
- model class implemented;
- propagation function implemented;
- KPI functions implemented;
- tests created;
- docs updated;
- how to build model inputs;
- how to run smoke test;
- how to run tests;
- known limitations and assumptions.

Known assumptions to report explicitly:

1. Productive accounts are identified by macrosector `{A, I, S}`.
2. Final demand accounts are identified by macrosector `{HH, CF, G, R}`.
3. Value-added accounts are identified by macrosector `{L, K, T}`.
4. `ROW` / macrosector `R` is treated as final demand.
5. `X0` is computed as `row_sum(Z0) + FD0`.
6. The propagation model operates only on productive accounts.
7. The old row-wise bottleneck approximation is preserved.
8. Demand and supply shocks are passed as explicit vectors.
