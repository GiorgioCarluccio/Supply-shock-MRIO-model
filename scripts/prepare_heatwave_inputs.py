import sys
from pathlib import Path

import geopandas as gpd
import xarray as xr


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.paths import CLIMATE_PROCESSED_DIR, RAW_EOBS_DIR, RAW_ISTAT_DIR

# Input files
TX_FILE = RAW_EOBS_DIR / "tx_ens_mean_0.1deg_reg_v33.0e.nc"
PROVINCES_SHP = RAW_ISTAT_DIR / "ProvCM01012024_g" / "ProvCM01012024_g_WGS84.shp"

# Output folder
OUTPUT_DIR = CLIMATE_PROCESSED_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TX_ITALY_OUTPUT = OUTPUT_DIR / "eobs_tx_italy_1991_2025.nc"
PROVINCES_OUTPUT = OUTPUT_DIR / "istat_provinces_2024.gpkg"

# Italy bounding box.
# Slightly wider than mainland Italy to include islands.
ITALY_BOUNDS = {
    "lat_min": 35.0,
    "lat_max": 48.5,
    "lon_min": 6.0,
    "lon_max": 19.5,
}

# For heatwave calibration, 1991-2020 is a useful climatological baseline.
# Keeping 1991-2025 is enough for the first MVP and much lighter than 1950-2025.
TIME_START = "1991-01-01"
TIME_END = "2025-12-31"


def inspect_tx_file() -> xr.Dataset:
    print("\n=== Opening E-OBS TX dataset ===")

    if not TX_FILE.exists():
        raise FileNotFoundError(f"TX file not found: {TX_FILE}")

    ds = xr.open_dataset(
        TX_FILE,
        chunks={"time": 365},
    )

    print("\nOriginal TX dataset:")
    print(ds)

    print("\nVariables:")
    for var_name, var in ds.data_vars.items():
        print(
            f"- {var_name}: shape={var.shape}, dtype={var.dtype}, "
            f"units={var.attrs.get('units')}, long_name={var.attrs.get('long_name')}"
        )

    return ds


def extract_italy_tx(ds: xr.Dataset) -> xr.Dataset:
    print("\n=== Extracting Italy bounding box and time window ===")

    italy = ds.sel(
        latitude=slice(ITALY_BOUNDS["lat_min"], ITALY_BOUNDS["lat_max"]),
        longitude=slice(ITALY_BOUNDS["lon_min"], ITALY_BOUNDS["lon_max"]),
        time=slice(TIME_START, TIME_END),
    )

    print("\nItaly TX subset:")
    print(italy)

    print("\nCoordinate ranges:")
    print(f"Time: {str(italy.time.values[0])} -> {str(italy.time.values[-1])}")
    print(f"Latitude: {float(italy.latitude.min())} -> {float(italy.latitude.max())}")
    print(f"Longitude: {float(italy.longitude.min())} -> {float(italy.longitude.max())}")

    return italy


def save_italy_tx(italy: xr.Dataset) -> None:
    print(f"\n=== Saving Italy TX subset ===")
    print(f"Output: {TX_ITALY_OUTPUT}")

    # Compression reduces disk usage, but may make writing slower.
    encoding = {}
    for var_name in italy.data_vars:
        encoding[var_name] = {
            "zlib": True,
            "complevel": 4,
            "dtype": "float32",
        }

    italy.to_netcdf(
        TX_ITALY_OUTPUT,
        engine="netcdf4",
        encoding=encoding,
    )

    check = xr.open_dataset(TX_ITALY_OUTPUT)
    print("\nSaved file verification:")
    print(check)


def inspect_provinces() -> gpd.GeoDataFrame:
    print("\n=== Opening ISTAT provinces shapefile ===")

    if not PROVINCES_SHP.exists():
        raise FileNotFoundError(f"Province shapefile not found: {PROVINCES_SHP}")

    provinces = gpd.read_file(PROVINCES_SHP)

    print("\nProvince layer:")
    print(provinces)

    print("\nCRS:")
    print(provinces.crs)

    print("\nColumns:")
    for col in provinces.columns:
        print(f"- {col}")

    print("\nFirst rows:")
    print(provinces.head())

    print("\nTotal features:")
    print(len(provinces))

    print("\nBounds:")
    print(provinces.total_bounds)

    return provinces


def save_clean_provinces(provinces: gpd.GeoDataFrame) -> None:
    print("\n=== Saving cleaned provinces layer ===")

    # Ensure WGS84.
    if provinces.crs is None:
        print("Warning: CRS is missing. Assuming EPSG:4326 because file name says WGS84.")
        provinces = provinces.set_crs("EPSG:4326")
    else:
        provinces = provinces.to_crs("EPSG:4326")

    provinces.to_file(
        PROVINCES_OUTPUT,
        layer="provinces",
        driver="GPKG",
    )

    print(f"Saved: {PROVINCES_OUTPUT}")


def main() -> None:
    ds = inspect_tx_file()
    italy = extract_italy_tx(ds)
    save_italy_tx(italy)

    provinces = inspect_provinces()
    save_clean_provinces(provinces)

    print("\n=== Done ===")
    print("Next step: compute provincial heatwave indicators from TX and ISTAT province geometries.")


if __name__ == "__main__":
    main()
