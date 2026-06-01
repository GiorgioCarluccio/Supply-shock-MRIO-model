"""Parse the raw ISPRA PIR workbook into a clean province exposure table.

The uploaded workbook (``data/raw/ispra/province_pir.xlsx``) has an unusual
layout: the first spreadsheet row holds long Italian descriptions, and the
*second* row holds the short machine codes (``cod_reg``, ``cod_prov``,
``provincia``, ``imidp*_p``, ``imfrp*_p``). Data starts on the third row, one
row per province.

Unit handling
-------------
The metadata labels mention percentages, but the observed values are stored as
fractions in ``[0, 1]``. The parser therefore validates units per column rather
than blindly dividing by 100::

    if max(value) <= 1.5: treat as share in [0, 1]
    else:                 treat as percentage and divide by 100
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd

# Sheet that holds the provincial data.
DATA_SHEET = "data"

# Short machine codes, located on the second spreadsheet row.
CODE_COLUMNS = ["cod_reg", "cod_prov", "provincia"]

# Hazard columns of interest (kept as shares in [0, 1] after parsing).
FLOOD_COLUMNS = ["imidp3_p", "imidp2_p", "imidp1_p"]
LANDSLIDE_COLUMNS = ["imfrp4_p", "imfrp3_p", "imfrp2_p", "imfrp1_p"]
HAZARD_COLUMNS: List[str] = FLOOD_COLUMNS + LANDSLIDE_COLUMNS

ALL_COLUMNS = CODE_COLUMNS + HAZARD_COLUMNS

EXPECTED_PROVINCES = 107

# Threshold below which a column is interpreted as a share rather than a %.
SHARE_MAX_THRESHOLD = 1.5


def _read_raw(path: Path) -> pd.DataFrame:
    """Read the ``data`` sheet using the short-code row as the header.

    The long-description row is on spreadsheet row 1 and the short codes are on
    spreadsheet row 2, so ``header=1`` selects the short codes as column names.
    """
    raw = pd.read_excel(path, sheet_name=DATA_SHEET, header=1)
    raw.columns = [str(c).strip() for c in raw.columns]
    return raw


def _normalise_units(values: pd.Series) -> pd.Series:
    """Return ``values`` as a share in ``[0, 1]``.

    Validates units instead of always dividing by 100: a column whose maximum
    is at most :data:`SHARE_MAX_THRESHOLD` is already a share; otherwise it is a
    percentage and is divided by 100.
    """
    numeric = pd.to_numeric(values, errors="coerce")
    observed_max = numeric.max(skipna=True)
    if pd.notna(observed_max) and observed_max > SHARE_MAX_THRESHOLD:
        numeric = numeric / 100.0
    return numeric


def parse_pir_workbook(path: Path) -> pd.DataFrame:
    """Parse the ISPRA PIR workbook into a clean exposure table.

    Returns a DataFrame with columns ``cod_reg``, ``cod_prov``, ``provincia``
    and the seven hazard columns, all hazard values expressed as shares in
    ``[0, 1]``.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"ISPRA PIR workbook not found: {path}. Place 'province_pir.xlsx' "
            "under data/raw/ispra/."
        )

    raw = _read_raw(path)

    missing = [c for c in ALL_COLUMNS if c not in raw.columns]
    if missing:
        raise ValueError(
            f"ISPRA workbook is missing expected columns {missing}. "
            f"Found columns: {list(raw.columns)}"
        )

    clean = raw[ALL_COLUMNS].copy()

    # Drop fully-empty trailing rows that Excel sometimes appends.
    clean = clean.dropna(how="all").reset_index(drop=True)
    clean = clean[clean["cod_prov"].notna()].reset_index(drop=True)

    clean["cod_reg"] = pd.to_numeric(clean["cod_reg"], errors="coerce").astype("Int64")
    clean["cod_prov"] = pd.to_numeric(clean["cod_prov"], errors="coerce").astype(
        "Int64"
    )
    clean["provincia"] = clean["provincia"].astype(str).str.strip()

    for col in HAZARD_COLUMNS:
        clean[col] = _normalise_units(clean[col])

    _validate(clean)
    return clean


def _validate(clean: pd.DataFrame) -> None:
    """Validate the cleaned PIR table; raise a clear error on any problem."""
    n = len(clean)
    if n != EXPECTED_PROVINCES:
        raise ValueError(
            f"Expected {EXPECTED_PROVINCES} provinces in the ISPRA workbook, "
            f"got {n}. Inspect the 'data' sheet layout."
        )
    if clean["cod_prov"].isna().any():
        raise ValueError("Some rows have a missing 'cod_prov'.")
    if clean["cod_prov"].duplicated().any():
        dups = clean.loc[clean["cod_prov"].duplicated(), "cod_prov"].tolist()
        raise ValueError(f"Duplicate 'cod_prov' values found: {dups}.")
    empty_names = clean["provincia"].isin(["", "nan", "None"])
    if empty_names.any():
        raise ValueError("Some rows have a missing province name.")
    for col in HAZARD_COLUMNS:
        if clean[col].isna().any():
            raise ValueError(f"Column '{col}' has non-numeric / missing values.")
        out_of_range = (clean[col] < 0) | (clean[col] > 1.0)
        if out_of_range.any():
            raise ValueError(
                f"Column '{col}' has values outside [0, 1] after unit handling; "
                "check the source units."
            )


def summarise(clean: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """Return per-column min / max / mean for logging and tests."""
    summary: Dict[str, Dict[str, float]] = {}
    for col in HAZARD_COLUMNS:
        summary[col] = {
            "min": float(clean[col].min()),
            "max": float(clean[col].max()),
            "mean": float(clean[col].mean()),
        }
    return summary
