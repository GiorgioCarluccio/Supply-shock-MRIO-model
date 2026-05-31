import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import box


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.paths import CLIMATE_MAPS_DIR, CLIMATE_PROCESSED_DIR

CLIMATE_DIR = CLIMATE_PROCESSED_DIR
MAP_DIR = CLIMATE_MAPS_DIR
MAP_DIR.mkdir(parents=True, exist_ok=True)

TX_ITALY_FILE = CLIMATE_DIR / "eobs_tx_italy_1991_2025.nc"
PROVINCES_GPKG = CLIMATE_DIR / "istat_provinces_2024.gpkg"
SUMMARY_CSV = CLIMATE_DIR / "province_heatwave_indicators.csv"

CELL_MAP_OUTPUT = MAP_DIR / "eobs_cells_hot_days_2011_2025.png"
PROVINCE_MAP_OUTPUT = MAP_DIR / "province_heatwave_exposure_weight.png"

HOT_DAY_THRESHOLD_C = 35.0
RECENT_START = "2011-01-01"
RECENT_END = "2025-12-31"


def clean_province_names(provinces: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    provinces = provinces.copy()

    provinces["province_name"] = provinces["DEN_PROV"]

    missing = provinces["province_name"].isna() | (provinces["province_name"] == "-")
    provinces.loc[missing, "province_name"] = provinces.loc[missing, "DEN_UTS"]

    missing = provinces["province_name"].isna() | (provinces["province_name"] == "-")
    provinces.loc[missing, "province_name"] = provinces.loc[missing, "DEN_CM"]

    provinces["province_code"] = provinces["COD_PROV"].astype(int)

    return provinces


def load_inputs() -> tuple[xr.Dataset, gpd.GeoDataFrame]:
    print("Loading TX dataset...")
    ds = xr.open_dataset(TX_ITALY_FILE, chunks={"time": 365})

    print("Loading provinces...")
    provinces = gpd.read_file(PROVINCES_GPKG, layer="provinces")
    provinces = provinces.to_crs("EPSG:4326")
    provinces = clean_province_names(provinces)

    return ds, provinces


def compute_recent_hot_days_by_cell(ds: xr.Dataset) -> pd.DataFrame:
    print("Computing recent mean annual hot days by E-OBS cell...")

    tx = ds["tx"].sel(time=slice(RECENT_START, RECENT_END))

    hot_days = tx >= HOT_DAY_THRESHOLD_C
    annual_hot_days = hot_days.groupby("time.year").sum(dim="time")
    mean_annual_hot_days = annual_hot_days.mean(dim="year").compute()

    df = mean_annual_hot_days.to_dataframe(
        name="hot_days_mean_2011_2025"
    ).reset_index()

    return df


def build_cell_polygons(df: pd.DataFrame, ds: xr.Dataset) -> gpd.GeoDataFrame:
    print("Building E-OBS cell polygons...")

    lats = ds["latitude"].values
    lons = ds["longitude"].values

    dlat = float(np.median(np.diff(lats)))
    dlon = float(np.median(np.diff(lons)))

    half_lat = dlat / 2.0
    half_lon = dlon / 2.0

    geometries = [
        box(
            row.longitude - half_lon,
            row.latitude - half_lat,
            row.longitude + half_lon,
            row.latitude + half_lat,
        )
        for row in df.itertuples(index=False)
    ]

    cells = gpd.GeoDataFrame(
        df.copy(),
        geometry=geometries,
        crs="EPSG:4326",
    )

    cells["grid_id"] = np.arange(len(cells))

    return cells


def assign_cells_to_italy(
    cells: gpd.GeoDataFrame,
    provinces: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    print("Assigning cells to Italian provinces using cell centroids...")

    centroids = cells.copy()
    centroids["geometry"] = centroids.geometry.centroid

    joined = gpd.sjoin(
        centroids,
        provinces[["province_code", "province_name", "geometry"]],
        how="inner",
        predicate="within",
    )

    assigned_ids = joined[["grid_id", "province_code", "province_name"]]

    cells_italy = cells.merge(
        assigned_ids,
        on="grid_id",
        how="inner",
    )

    cells_italy = gpd.GeoDataFrame(
        cells_italy,
        geometry="geometry",
        crs="EPSG:4326",
    )

    print(f"Cells inside Italian provinces: {len(cells_italy)}")

    return cells_italy


def plot_cell_map(cells_italy: gpd.GeoDataFrame, provinces: gpd.GeoDataFrame) -> None:
    print("Plotting E-OBS cell map...")

    fig, ax = plt.subplots(figsize=(10, 12))

    cells_italy.plot(
        ax=ax,
        column="hot_days_mean_2011_2025",
        legend=True,
        cmap="inferno",
        linewidth=0.05,
        edgecolor="none",
        legend_kwds={
            "label": "Mean annual hot days, TX >= 35°C, 2011-2025",
            "shrink": 0.65,
        },
    )

    provinces.boundary.plot(
        ax=ax,
        linewidth=0.35,
        color="black",
    )

    ax.set_title(
        "E-OBS grid cells over Italian provinces\n"
        "Mean annual hot days, TX >= 35°C, 2011-2025",
        fontsize=12,
    )

    ax.set_axis_off()
    plt.tight_layout()

    fig.savefig(CELL_MAP_OUTPUT, dpi=300)
    plt.close(fig)

    print(f"Saved: {CELL_MAP_OUTPUT}")


def plot_province_exposure_map(provinces: gpd.GeoDataFrame) -> None:
    print("Plotting provincial exposure-weight map...")

    summary = pd.read_csv(SUMMARY_CSV)

    provinces_map = provinces.merge(
        summary[
            [
                "province_code",
                "heatwave_exposure_weight",
                "heatwave_exposure_weight_unclipped",
            ]
        ],
        on="province_code",
        how="left",
    )

    fig, ax = plt.subplots(figsize=(10, 12))

    provinces_map.plot(
        ax=ax,
        column="heatwave_exposure_weight",
        legend=True,
        cmap="magma",
        edgecolor="black",
        linewidth=0.35,
        legend_kwds={
            "label": "Heatwave exposure weight",
            "shrink": 0.65,
        },
    )

    ax.set_title(
        "Provincial heatwave exposure weight\n"
        "p75 grid-cell hot days, attenuated and clipped",
        fontsize=12,
    )

    ax.set_axis_off()
    plt.tight_layout()

    fig.savefig(PROVINCE_MAP_OUTPUT, dpi=300)
    plt.close(fig)

    print(f"Saved: {PROVINCE_MAP_OUTPUT}")


def main() -> None:
    ds, provinces = load_inputs()

    cell_df = compute_recent_hot_days_by_cell(ds)
    cells = build_cell_polygons(cell_df, ds)
    cells_italy = assign_cells_to_italy(cells, provinces)

    plot_cell_map(cells_italy, provinces)
    plot_province_exposure_map(provinces)

    print("Done.")


if __name__ == "__main__":
    main()
