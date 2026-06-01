"""Province crosswalk and canonical hazard exposure table.

This module connects the two province identifier systems used in the project:

* climate exposure files use ISTAT numeric province codes (``cod_prov``);
* the productive SAM nodes use NUTS-3 2021 region codes (``ITC11`` ...).

It also assembles the canonical long-format hazard exposure table that the
shock matrix consumes, combining heatwave indicators with the cleaned ISPRA
flood / landslide shares.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from . import (
    EXPOSURE_WEIGHT_ATTENUATION,
    EXPOSURE_WEIGHT_CLIP,
    FLOOD,
    HEATWAVE,
    LANDSLIDE,
)
from .pir_parser import FLOOD_COLUMNS, LANDSLIDE_COLUMNS

# --------------------------------------------------------------------------- #
# NUTS-3 2021 -> ISTAT car-plate abbreviation (SIGLA)
# --------------------------------------------------------------------------- #
# This mapping is reference data. It is validated at build time against the
# ISTAT provinces layer (bijective, 107 provinces) so a transcription error
# fails loudly rather than silently mis-assigning exposure.
NUTS_TO_SIGLA: Dict[str, str] = {
    # Piemonte + Valle d'Aosta
    "ITC11": "TO", "ITC12": "VC", "ITC13": "BI", "ITC14": "VB", "ITC15": "NO",
    "ITC16": "CN", "ITC17": "AT", "ITC18": "AL", "ITC20": "AO",
    # Liguria
    "ITC31": "IM", "ITC32": "SV", "ITC33": "GE", "ITC34": "SP",
    # Lombardia
    "ITC41": "VA", "ITC42": "CO", "ITC43": "LC", "ITC44": "SO", "ITC46": "BG",
    "ITC47": "BS", "ITC48": "PV", "ITC49": "CR", "ITC4A": "MN", "ITC4B": "LO",
    "ITC4C": "MI", "ITC4D": "MB",
    # Abruzzo
    "ITF11": "AQ", "ITF12": "TE", "ITF13": "PE", "ITF14": "CH",
    # Molise
    "ITF21": "IS", "ITF22": "CB",
    # Campania
    "ITF31": "CE", "ITF32": "BN", "ITF33": "NA", "ITF34": "AV", "ITF35": "SA",
    # Puglia
    "ITF43": "BT", "ITF44": "FG", "ITF45": "BA", "ITF46": "TA", "ITF47": "BR",
    "ITF48": "LE",
    # Basilicata
    "ITF51": "PZ", "ITF52": "MT",
    # Calabria
    "ITF61": "CS", "ITF62": "KR", "ITF63": "CZ", "ITF64": "VV", "ITF65": "RC",
    # Sicilia
    "ITG11": "TP", "ITG12": "PA", "ITG13": "ME", "ITG14": "AG", "ITG15": "CL",
    "ITG16": "EN", "ITG17": "CT", "ITG18": "RG", "ITG19": "SR",
    # Sardegna
    "ITG2D": "SS", "ITG2E": "NU", "ITG2F": "CA", "ITG2G": "OR", "ITG2H": "SU",
    # Trentino-Alto Adige + Veneto
    "ITH10": "BZ", "ITH20": "TN", "ITH31": "VR", "ITH32": "VI", "ITH33": "BL",
    "ITH34": "TV", "ITH35": "VE", "ITH36": "PD", "ITH37": "RO",
    # Friuli-Venezia Giulia
    "ITH41": "PN", "ITH42": "UD", "ITH43": "GO", "ITH44": "TS",
    # Emilia-Romagna
    "ITH51": "PC", "ITH52": "PR", "ITH53": "RE", "ITH54": "MO", "ITH55": "BO",
    "ITH56": "FE", "ITH57": "RA", "ITH58": "FC", "ITH59": "RN",
    # Toscana
    "ITI11": "MS", "ITI12": "LU", "ITI13": "PT", "ITI14": "FI", "ITI15": "PO",
    "ITI16": "LI", "ITI17": "PI", "ITI18": "AR", "ITI19": "SI", "ITI1A": "GR",
    # Umbria
    "ITI21": "PG", "ITI22": "TR",
    # Marche
    "ITI31": "PU", "ITI32": "AN", "ITI33": "MC", "ITI34": "AP", "ITI35": "FM",
    # Lazio
    "ITI41": "VT", "ITI42": "RI", "ITI43": "RM", "ITI44": "LT", "ITI45": "FR",
}

# Mapping of hazard / severity to the source exposure column.
FLOOD_SEVERITY_COLUMN = {"low": "imidp1_p", "medium": "imidp2_p", "high": "imidp3_p"}
LANDSLIDE_SEVERITY_COLUMN = {
    "p1": "imfrp1_p",
    "p2": "imfrp2_p",
    "p3": "imfrp3_p",
    "p4": "imfrp4_p",
}


# --------------------------------------------------------------------------- #
# Province crosswalk
# --------------------------------------------------------------------------- #
def build_province_crosswalk(provinces_gpkg: Path) -> pd.DataFrame:
    """Build the NUTS-3 <-> ISTAT province crosswalk from the ISTAT layer.

    Joins the embedded :data:`NUTS_TO_SIGLA` reference with the authoritative
    ISTAT provinces layer (``COD_PROV``, ``SIGLA``, ``DEN_UTS``) on the car-plate
    abbreviation. The result is validated to be a bijection over 107 provinces.

    Returns a DataFrame with columns ``province_code`` (ISTAT numeric),
    ``province_name``, ``province_abbr`` and ``region_code`` (NUTS-3).
    """
    import geopandas as gpd  # local import: geopandas is heavy to import.

    provinces_gpkg = Path(provinces_gpkg)
    if not provinces_gpkg.exists():
        raise FileNotFoundError(
            f"ISTAT provinces layer not found: {provinces_gpkg}. It is required "
            "to build the province crosswalk."
        )

    layer = gpd.read_file(provinces_gpkg)
    required = {"COD_PROV", "SIGLA", "DEN_UTS"}
    missing = required - set(layer.columns)
    if missing:
        raise ValueError(
            f"ISTAT provinces layer is missing columns {sorted(missing)}."
        )

    istat = (
        pd.DataFrame(layer.drop(columns=layer.geometry.name))
        if hasattr(layer, "geometry")
        else pd.DataFrame(layer)
    )
    istat = istat[["COD_PROV", "SIGLA", "DEN_UTS"]].copy()
    istat["SIGLA"] = istat["SIGLA"].astype(str).str.strip()

    nuts = pd.DataFrame(
        {"region_code": list(NUTS_TO_SIGLA), "SIGLA": list(NUTS_TO_SIGLA.values())}
    )

    merged = nuts.merge(istat, on="SIGLA", how="left")
    if merged["COD_PROV"].isna().any():
        bad = merged.loc[merged["COD_PROV"].isna(), ["region_code", "SIGLA"]]
        raise ValueError(
            "NUTS-3 codes did not match any ISTAT province abbreviation:\n"
            f"{bad.to_string(index=False)}"
        )

    crosswalk = pd.DataFrame(
        {
            "province_code": merged["COD_PROV"].astype(int),
            "province_name": merged["DEN_UTS"].astype(str).str.strip(),
            "province_abbr": merged["SIGLA"].astype(str),
            "region_code": merged["region_code"].astype(str),
        }
    ).sort_values("province_code").reset_index(drop=True)

    _validate_crosswalk(crosswalk)
    return crosswalk


def _validate_crosswalk(crosswalk: pd.DataFrame) -> None:
    if len(crosswalk) != len(NUTS_TO_SIGLA):
        raise ValueError(
            f"Crosswalk has {len(crosswalk)} rows, expected {len(NUTS_TO_SIGLA)}."
        )
    if crosswalk["province_code"].duplicated().any():
        raise ValueError("Crosswalk has duplicate province_code values.")
    if crosswalk["region_code"].duplicated().any():
        raise ValueError("Crosswalk has duplicate region_code values.")


def load_crosswalk(path: Path) -> pd.DataFrame:
    """Load a previously written crosswalk CSV, with a clear missing-file error."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Province crosswalk not found: {path}. Build it first with "
            "scripts/build_hazard_exposure_table.py (it writes "
            "data/processed/mappings/province_code_crosswalk.csv)."
        )
    crosswalk = pd.read_csv(path)
    required = {"province_code", "province_name", "province_abbr", "region_code"}
    missing = required - set(crosswalk.columns)
    if missing:
        raise ValueError(f"Crosswalk is missing columns {sorted(missing)}.")
    crosswalk["province_code"] = crosswalk["province_code"].astype(int)
    crosswalk["region_code"] = crosswalk["region_code"].astype(str)
    return crosswalk


# --------------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------------- #
def load_heatwave_indicators(path: Path) -> pd.DataFrame:
    """Load the validated provincial heatwave indicators."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Heatwave indicators not found: {path}.")
    hw = pd.read_csv(path, encoding="utf-8-sig")
    required = {
        "province_code",
        "province_name",
        "heatwave_exposure_raw",
        "heatwave_exposure_weight",
    }
    missing = required - set(hw.columns)
    if missing:
        raise ValueError(f"Heatwave indicators missing columns {sorted(missing)}.")
    hw["province_code"] = hw["province_code"].astype(int)
    return hw


# --------------------------------------------------------------------------- #
# Canonical hazard exposure table
# --------------------------------------------------------------------------- #
def _attenuated_weight(raw: np.ndarray) -> np.ndarray:
    """Relative-exposure weight clipped to the configured range (visualisation)."""
    raw = np.asarray(raw, dtype=float)
    national_mean = raw[raw > 0].mean() if (raw > 0).any() else 0.0
    if national_mean <= 0:
        return np.ones_like(raw)
    relative = raw / national_mean
    weight = 1.0 + EXPOSURE_WEIGHT_ATTENUATION * (relative - 1.0)
    return np.clip(weight, EXPOSURE_WEIGHT_CLIP[0], EXPOSURE_WEIGHT_CLIP[1])


def _province_identity(crosswalk: pd.DataFrame) -> pd.DataFrame:
    return crosswalk[["province_code", "province_name", "province_abbr"]].copy()


def build_hazard_exposure_table(
    heatwave: pd.DataFrame, pir_clean: pd.DataFrame, crosswalk: pd.DataFrame
) -> pd.DataFrame:
    """Build the canonical long-format hazard exposure table.

    One row per ``province x hazard x severity`` with columns:
    ``province_code, province_name, province_abbr, hazard, severity,
    raw_exposure, exposure_weight, exposure_type, source_file, source_column,
    method``.
    """
    identity = _province_identity(crosswalk)
    rows = []

    # ---- Heatwave (severity = central) ----
    hw = heatwave[
        ["province_code", "heatwave_exposure_raw", "heatwave_exposure_weight"]
    ].copy()
    hw = hw.merge(identity, on="province_code", how="inner")
    rows.append(
        pd.DataFrame(
            {
                "province_code": hw["province_code"],
                "province_name": hw["province_name"],
                "province_abbr": hw["province_abbr"],
                "hazard": HEATWAVE,
                "severity": "central",
                "raw_exposure": hw["heatwave_exposure_raw"].astype(float),
                "exposure_weight": hw["heatwave_exposure_weight"].astype(float),
                "exposure_type": "heatwave_hot_days_p75_annual_average",
                "source_file": "province_heatwave_indicators.csv",
                "source_column": "heatwave_exposure_raw / heatwave_exposure_weight",
                "method": (
                    "validated heatwave exposure weight "
                    "(relative to national mean, attenuated, clipped 0.10-3.00)"
                ),
            }
        )
    )

    # ---- Flood + landslide (impacted business shares) ----
    pir = pir_clean.rename(columns={"cod_prov": "province_code"})
    pir["province_code"] = pir["province_code"].astype(int)
    pir = pir.merge(identity, on="province_code", how="inner")

    severity_specs = [
        (FLOOD, "low", FLOOD_SEVERITY_COLUMN["low"]),
        (FLOOD, "medium", FLOOD_SEVERITY_COLUMN["medium"]),
        (FLOOD, "high", FLOOD_SEVERITY_COLUMN["high"]),
        (LANDSLIDE, "p1", LANDSLIDE_SEVERITY_COLUMN["p1"]),
        (LANDSLIDE, "p2", LANDSLIDE_SEVERITY_COLUMN["p2"]),
        (LANDSLIDE, "p3", LANDSLIDE_SEVERITY_COLUMN["p3"]),
        (LANDSLIDE, "p4", LANDSLIDE_SEVERITY_COLUMN["p4"]),
    ]
    for hazard, severity, column in severity_specs:
        raw = pir[column].astype(float).to_numpy()
        rows.append(
            pd.DataFrame(
                {
                    "province_code": pir["province_code"],
                    "province_name": pir["province_name"],
                    "province_abbr": pir["province_abbr"],
                    "hazard": hazard,
                    "severity": severity,
                    "raw_exposure": raw,
                    "exposure_weight": _attenuated_weight(raw),
                    "exposure_type": "impacted_business_share",
                    "source_file": "province_pir_clean.csv",
                    "source_column": column,
                    "method": (
                        "ISPRA local business units at risk share "
                        "(relative-exposure weight for visualisation only)"
                    ),
                }
            )
        )

    table = pd.concat(rows, ignore_index=True)
    _validate_exposure_table(table, crosswalk)
    return table


def _validate_exposure_table(table: pd.DataFrame, crosswalk: pd.DataFrame) -> None:
    n_prov = crosswalk["province_code"].nunique()
    counts = table.groupby(["hazard", "severity"])["province_code"].nunique()
    short = counts[counts != n_prov]
    if not short.empty:
        raise ValueError(
            "Some hazard/severity combinations do not cover all provinces:\n"
            f"{short.to_string()}"
        )
    if table["raw_exposure"].isna().any():
        raise ValueError("Hazard exposure table has null raw_exposure values.")
