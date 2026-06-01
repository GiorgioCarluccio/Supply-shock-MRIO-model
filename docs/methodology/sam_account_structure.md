# SAM account structure

The modelling layer consumes the dense SAM artifact produced by the ingestion
pipeline (`data/processed/sam/`). This note documents the account structure the
model relies on.

## Source table

```text
ml.sam.mrsam_downscaled_y   (long format)
```

Relevant columns (standardized internal names in parentheses):

```text
region_orig  (origin_region)        row region / seller account region
ind_ava      (origin_sector)        row sector / seller account sector
region_dest  (destination_region)   column region / buyer account region
ind_use      (destination_sector)   column sector / buyer account sector
value        (flow_value)           SAM cell value
row_label                           full row account label
col_label                           full column account label
```

## Matrix orientation

```text
row    = seller / supplier / origin / producing account
column = buyer / destination / using account
Z[i, j] = value supplied by seller i and purchased/used by buyer j
```

The monetary payment direction is column `j` -> row `i`; the matrix orientation
is the standard IO accounting orientation (`row = seller`, `column = buyer`).

## Account labels

Each account has a canonical label with **double underscore** separators:

```text
region_code__sector_code__macrosector_code
```

Examples:

```text
ITC11__A01__A        EU-ITA__LAB__L       EU-ITA__HH__HH
ITC11__C10-12__I     EU-ITA__CAP__K       EU-ITA__CF__CF
ITC11__M69_70__S     EU-ITA__TAX__T       EU-ITA__GOV__G
                                          EU-ITA__ROW__R
```

A label that does not split into exactly three non-empty parts is a validation
error (`label_parser.parse_account_label`).

### Macrosector recovery

The macrosector is the **third** part of `row_label` / `col_label`. It is the
primary classification key and depends only on the sector code (consistently
across regions). The dense ingestion (`build_sam_dense_matrix_from_databricks.py`)
now carries it into `nodes.csv`. Artifacts built before this change can be
upgraded locally — without Databricks — from the interim parquet labels via
`scripts/enrich_sam_nodes_with_macrosector.py`.

Note the macrosector is **not** a naive NACE-letter heuristic: e.g. `E36 -> I`
but `E37-39 -> S`, and the real-estate sector `L -> S` while labour `LAB -> L`.
This is why it must be read from the labels.

## Account classification

```text
productive macrosectors    = {A, I, S}
value-added macrosectors   = {L, K, T}
final-demand columns       = {HH, CF, G, R}
external/input rows        = {R} when ROW sells into productive columns
```

| macrosector | meaning              | class         |
|-------------|----------------------|---------------|
| A           | agriculture          | productive    |
| I           | industry             | productive    |
| S           | services             | productive    |
| L           | labour               | value_added   |
| K           | capital              | value_added   |
| T           | indirect taxes       | value_added   |
| HH          | households           | final_demand  |
| CF          | capital formation    | final_demand  |
| G           | government           | final_demand  |
| R           | rest of world        | final_demand column / external input row |

`ROW` is role-specific. As a column, `EU-ITA__ROW__R` is final demand
(exports/rest-of-world absorption) and contributes to `FD0`. As a row into
productive columns, it represents imported/external inputs used by production
and contributes to `IMP0`, not to productive output. This split is required for
row-vs-column accounting: excluding the ROW input row creates a large apparent
gap, while including it reconciles productive row output with productive column
inputs up to rounding.

In the current Italian SAM (`mrsam_euita_2022_3oe`) the 7 institutional accounts
(`LAB`, `CAP`, `TAX`, `HH`, `CF`, `GOV`, `ROW`) exist only under the national
region `EU-ITA`; all other (region, sector) nodes are productive. This yields
6462 productive nodes out of 6469 accounts.
