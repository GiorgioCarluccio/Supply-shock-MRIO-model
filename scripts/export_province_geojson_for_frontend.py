"""Export Italian province geometry to a frontend-ready GeoJSON file.

Reads the ISTAT 2024 province shapefile, reprojects to WGS84 (EPSG:4326),
simplifies the geometry for web delivery, and aligns the feature properties
with the province-code crosswalk used by the model/dashboard data.

Output:
    frontend/public/data/geographies/italy_provinces.geojson

Properties written on each feature (where available):
    province_code   numeric ISTAT province code (COD_PROV / COD_UTS)
    province_name   province / metropolitan-city name
    province_abbr   two-letter plate code (SIGLA)
    region_code     NUTS-3 code used as the join key in dashboard data

The script fails clearly if the crosswalk cannot map a province so that
broken joins are caught before they reach the frontend.

Usage (from repo root):
    .venv/Scripts/python.exe scripts/export_province_geojson_for_frontend.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import geopandas as gpd


def _coalesce(value, fallback):
    """Return value unless it is None/NaN/blank, else fallback.

    pandas reads missing cells as float NaN, which is *truthy* in Python (so a
    plain ``value or fallback`` does not work) and is invalid JSON, which would
    break ``fetch().json()`` in the browser. Strip it here.
    """
    if value is None:
        return fallback
    if isinstance(value, float) and math.isnan(value):
        return fallback
    if isinstance(value, str) and value.strip() == "":
        return fallback
    return value

# --- paths (resolved relative to the repo root, never hardcoded) ------------
REPO_ROOT = Path(__file__).resolve().parents[1]
SHAPEFILE = (
    REPO_ROOT
    / "data"
    / "raw"
    / "istat"
    / "ProvCM01012024_g"
    / "ProvCM01012024_g_WGS84.shp"
)
CROSSWALK = REPO_ROOT / "data" / "processed" / "mappings" / "province_code_crosswalk.csv"
OUT_DIR = REPO_ROOT / "frontend" / "public" / "data" / "geographies"
OUT_FILE = OUT_DIR / "italy_provinces.geojson"

# Geometry simplification tolerance in degrees (~0.005 deg ~= 500 m).
# Keeps province outlines recognisable while shrinking the payload.
SIMPLIFY_TOLERANCE = 0.005
COORD_PRECISION = 5


def main() -> int:
    if not SHAPEFILE.exists():
        print(f"ERROR: shapefile not found: {SHAPEFILE}", file=sys.stderr)
        return 1
    if not CROSSWALK.exists():
        print(f"ERROR: crosswalk not found: {CROSSWALK}", file=sys.stderr)
        return 1

    print(f"Reading shapefile: {SHAPEFILE}")
    gdf = gpd.read_file(SHAPEFILE)
    print(f"  {len(gdf)} province features, CRS={gdf.crs}")

    # Reproject to WGS84 for web maps.
    if gdf.crs is None:
        print("ERROR: shapefile has no CRS; cannot reproject safely", file=sys.stderr)
        return 1
    gdf = gdf.to_crs(epsg=4326)

    # Simplify geometry to reduce payload size.
    gdf["geometry"] = gdf.geometry.simplify(
        SIMPLIFY_TOLERANCE, preserve_topology=True
    )

    # --- load crosswalk (province_code -> region_code/name/abbr) -----------
    import pandas as pd

    # keep_default_na=False so plate codes like "NA" (Napoli) are read as the
    # string "NA" and NOT coerced to NaN by pandas' default missing-value list.
    xwalk = pd.read_csv(CROSSWALK, keep_default_na=False, na_values=[""])
    xwalk["province_code"] = xwalk["province_code"].astype(int)
    xwalk_by_code = xwalk.set_index("province_code").to_dict("index")

    # COD_UTS is the unique unit code (provinces + metropolitan cities); it
    # matches the crosswalk province_code. COD_PROV is 0 for metro cities, so
    # prefer COD_UTS and fall back to COD_PROV.
    def resolve_code(row) -> int:
        for col in ("COD_UTS", "COD_PROV", "COD_CM"):
            val = row.get(col)
            if val is not None and int(val) in xwalk_by_code:
                return int(val)
        # last resort: raw COD_PROV
        return int(row.get("COD_PROV", 0))

    features = []
    unmatched = []
    for _, row in gdf.iterrows():
        code = resolve_code(row)
        meta = xwalk_by_code.get(code)
        if meta is None:
            unmatched.append((code, row.get("DEN_UTS")))
            continue
        geom = row.geometry
        if geom is None or geom.is_empty:
            unmatched.append((code, row.get("DEN_UTS")))
            continue
        props = {
            "province_code": code,
            "province_name": _coalesce(meta.get("province_name"), row.get("DEN_UTS")),
            "province_abbr": _coalesce(meta.get("province_abbr"), row.get("SIGLA")),
            "region_code": _coalesce(meta.get("region_code"), None),
        }
        features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": _round_geometry(geom.__geo_interface__, COORD_PRECISION),
            }
        )

    if unmatched:
        print(
            f"ERROR: {len(unmatched)} province feature(s) could not be matched "
            f"to the crosswalk: {unmatched[:10]}",
            file=sys.stderr,
        )
        return 1

    fc = {"type": "FeatureCollection", "features": features}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8") as fh:
        # allow_nan=False guarantees strictly valid JSON (no bare NaN/Infinity
        # tokens), which browsers' JSON.parse rejects.
        json.dump(fc, fh, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

    size_kb = OUT_FILE.stat().st_size / 1024
    print(f"Wrote {len(features)} features -> {OUT_FILE} ({size_kb:.0f} KB)")
    return 0


def _round_geometry(geom: dict, precision: int) -> dict:
    """Recursively round coordinate floats to shrink the payload."""

    def _round_coords(coords):
        if isinstance(coords, (list, tuple)):
            if coords and isinstance(coords[0], (int, float)):
                return [round(float(c), precision) for c in coords]
            return [_round_coords(c) for c in coords]
        return coords

    geom = dict(geom)
    if "coordinates" in geom:
        geom["coordinates"] = _round_coords(geom["coordinates"])
    return geom


if __name__ == "__main__":
    raise SystemExit(main())
