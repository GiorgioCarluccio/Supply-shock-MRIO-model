import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.paths import CLIMATE_PROCESSED_DIR

INPUT_DIR = CLIMATE_PROCESSED_DIR

TX_ITALY_FILE = INPUT_DIR / "eobs_tx_italy_1991_2025.nc"
PROVINCES_GPKG = INPUT_DIR / "istat_provinces_2024.gpkg"

OUTPUT_SUMMARY_CSV = INPUT_DIR / "province_heatwave_indicators.csv"
OUTPUT_YEARLY_CSV = INPUT_DIR / "province_heatwave_indicators_yearly.csv"

HOT_DAY_THRESHOLD_C = 35.0

RECENT_START_YEAR = 2011
RECENT_END_YEAR = 2025

BASELINE_START_YEAR = 1991
BASELINE_END_YEAR = 2020

MIN_EXPOSURE_WEIGHT = 0.10
MAX_EXPOSURE_WEIGHT = 3.00
EXPOSURE_ATTENUATION = 0.50


def load_inputs() -> tuple[xr.Dataset, gpd.GeoDataFrame]:
    print("\n=== Loading TX Italy dataset ===")

    if not TX_ITALY_FILE.exists():
        raise FileNotFoundError(f"TX Italy file not found: {TX_ITALY_FILE}")

    ds = xr.open_dataset(
        TX_ITALY_FILE,
        chunks={"time": 365},
    )

    print(ds)

    if "tx" not in ds.data_vars:
        raise ValueError("Expected variable 'tx' not found in NetCDF file.")

    print("\n=== Loading ISTAT provinces ===")

    if not PROVINCES_GPKG.exists():
        raise FileNotFoundError(f"Province GeoPackage not found: {PROVINCES_GPKG}")

    provinces = gpd.read_file(PROVINCES_GPKG, layer="provinces")

    if provinces.crs is None:
        raise ValueError("Province layer CRS is missing.")

    provinces = provinces.to_crs("EPSG:4326")

    provinces = clean_province_names(provinces)

    print(
        provinces[
            [
                "COD_PROV",
                "province_name",
                "SIGLA",
                "TIPO_UTS",
            ]
        ].head()
    )

    print(f"Number of provinces: {len(provinces)}")

    return ds, provinces


def clean_province_names(provinces: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    provinces = provinces.copy()

    provinces["province_name"] = provinces["DEN_PROV"]

    missing = provinces["province_name"].isna() | (provinces["province_name"] == "-")
    if "DEN_UTS" in provinces.columns:
        provinces.loc[missing, "province_name"] = provinces.loc[missing, "DEN_UTS"]

    missing = provinces["province_name"].isna() | (provinces["province_name"] == "-")
    if "DEN_CM" in provinces.columns:
        provinces.loc[missing, "province_name"] = provinces.loc[missing, "DEN_CM"]

    missing = provinces["province_name"].isna() | (provinces["province_name"] == "-")
    if missing.any():
        provinces.loc[missing, "province_name"] = (
            "Province_" + provinces.loc[missing, "COD_PROV"].astype(str)
        )

    provinces["province_code"] = provinces["COD_PROV"].astype(int)
    provinces["province_abbr"] = provinces["SIGLA"].astype(str)

    return provinces


def build_grid_points(ds: xr.Dataset) -> gpd.GeoDataFrame:
    print("\n=== Building E-OBS grid-cell points ===")

    lats = ds["latitude"].values
    lons = ds["longitude"].values

    lon_grid, lat_grid = np.meshgrid(lons, lats)

    grid_df = pd.DataFrame(
        {
            "latitude": lat_grid.ravel(),
            "longitude": lon_grid.ravel(),
        }
    )

    grid_df["grid_id"] = np.arange(len(grid_df))

    grid_gdf = gpd.GeoDataFrame(
        grid_df,
        geometry=gpd.points_from_xy(grid_df["longitude"], grid_df["latitude"]),
        crs="EPSG:4326",
    )

    print(f"Total grid points in Italy bounding box: {len(grid_gdf)}")

    return grid_gdf


def assign_grid_points_to_provinces(
    grid_gdf: gpd.GeoDataFrame,
    provinces: gpd.GeoDataFrame,
) -> pd.DataFrame:
    print("\n=== Assigning grid points to provinces ===")

    province_cols = [
        "province_code",
        "province_name",
        "province_abbr",
        "geometry",
    ]

    joined = gpd.sjoin(
        grid_gdf,
        provinces[province_cols],
        how="inner",
        predicate="within",
    )

    mapping = pd.DataFrame(
        joined.drop(columns=["geometry", "index_right"])
    )

    print(f"Grid points inside Italian provinces: {len(mapping)}")

    print("\nGrid points per province, first rows:")
    print(
        mapping.groupby(["province_code", "province_name", "province_abbr"])
        .size()
        .reset_index(name="n_grid_cells")
        .head()
    )

    return mapping


def compute_annual_hot_days(ds: xr.Dataset) -> pd.DataFrame:
    print("\n=== Computing annual hot days per grid cell ===")
    print(f"Hot day threshold: TX >= {HOT_DAY_THRESHOLD_C}°C")

    tx = ds["tx"]

    hot_days = tx >= HOT_DAY_THRESHOLD_C

    annual_hot_days = hot_days.groupby("time.year").sum(dim="time")

    print("\nAnnual hot days xarray object:")
    print(annual_hot_days)

    print("\nComputing annual hot days. This may take a few minutes...")
    annual_hot_days = annual_hot_days.compute()

    df = annual_hot_days.to_dataframe(name="annual_hot_days").reset_index()

    print("\nAnnual hot days dataframe:")
    print(df.head())
    print(f"Rows: {len(df)}")

    return df


def aggregate_to_provinces(
    annual_hot_days_df: pd.DataFrame,
    grid_mapping: pd.DataFrame,
) -> pd.DataFrame:
    print("\n=== Aggregating hot days to provinces ===")

    merged = annual_hot_days_df.merge(
        grid_mapping[
            [
                "latitude",
                "longitude",
                "province_code",
                "province_name",
                "province_abbr",
            ]
        ],
        on=["latitude", "longitude"],
        how="inner",
    )

    province_year = (
        merged.groupby(
            ["province_code", "province_name", "province_abbr", "year"],
            as_index=False,
        )
        .agg(
            hot_days_mean=("annual_hot_days", "mean"),
            hot_days_median=("annual_hot_days", "median"),
            hot_days_p75=("annual_hot_days", lambda x: float(np.percentile(x, 75))),
            hot_days_p90=("annual_hot_days", lambda x: float(np.percentile(x, 90))),
            hot_days_max=("annual_hot_days", "max"),
            n_grid_cells=("annual_hot_days", "count"),
        )
    )

    print("\nProvince-year indicators:")
    print(province_year.head())

    return province_year


def summarize_period(
    province_year: pd.DataFrame,
    start_year: int,
    end_year: int,
    suffix: str,
) -> pd.DataFrame:
    period = province_year[
        (province_year["year"] >= start_year)
        & (province_year["year"] <= end_year)
    ]

    summary = (
        period.groupby(
            ["province_code", "province_name", "province_abbr"],
            as_index=False,
        )
        .agg(
            **{
                f"hot_days_mean_avg_{suffix}": ("hot_days_mean", "mean"),
                f"hot_days_mean_p95_{suffix}": (
                    "hot_days_mean",
                    lambda x: float(np.percentile(x, 95)),
                ),
                f"hot_days_p75_avg_{suffix}": ("hot_days_p75", "mean"),
                f"hot_days_p75_p95_{suffix}": (
                    "hot_days_p75",
                    lambda x: float(np.percentile(x, 95)),
                ),
                f"hot_days_p90_avg_{suffix}": ("hot_days_p90", "mean"),
                f"hot_days_p90_p95_{suffix}": (
                    "hot_days_p90",
                    lambda x: float(np.percentile(x, 95)),
                ),
                f"hot_days_max_avg_{suffix}": ("hot_days_max", "mean"),
                f"hot_days_max_p95_{suffix}": (
                    "hot_days_max",
                    lambda x: float(np.percentile(x, 95)),
                ),
                f"n_years_{suffix}": ("year", "nunique"),
                "n_grid_cells": ("n_grid_cells", "median"),
            }
        )
    )

    return summary


def relative_weight(series: pd.Series) -> pd.Series:
    national_mean = series.mean()

    if national_mean == 0 or pd.isna(national_mean):
        raise ValueError("National mean is zero or NaN. Check input data.")

    return series / national_mean


def attenuated_relative_weight(series: pd.Series) -> pd.Series:
    rel = relative_weight(series)

    attenuated = 1.0 + EXPOSURE_ATTENUATION * (rel - 1.0)

    return attenuated.clip(
        lower=MIN_EXPOSURE_WEIGHT,
        upper=MAX_EXPOSURE_WEIGHT,
    )


def compute_summary_indicators(province_year: pd.DataFrame) -> pd.DataFrame:
    print("\n=== Computing provincial summary indicators ===")

    baseline_suffix = f"{BASELINE_START_YEAR}_{BASELINE_END_YEAR}"
    recent_suffix = f"{RECENT_START_YEAR}_{RECENT_END_YEAR}"

    baseline_summary = summarize_period(
        province_year=province_year,
        start_year=BASELINE_START_YEAR,
        end_year=BASELINE_END_YEAR,
        suffix=baseline_suffix,
    )

    recent_summary = summarize_period(
        province_year=province_year,
        start_year=RECENT_START_YEAR,
        end_year=RECENT_END_YEAR,
        suffix=recent_suffix,
    )

    summary = baseline_summary.merge(
        recent_summary,
        on=[
            "province_code",
            "province_name",
            "province_abbr",
            "n_grid_cells",
        ],
        how="outer",
    )

    recent_mean_col = f"hot_days_mean_avg_{recent_suffix}"
    recent_p75_col = f"hot_days_p75_avg_{recent_suffix}"
    recent_p90_col = f"hot_days_p90_avg_{recent_suffix}"

    summary["heatwave_exposure_raw_mean"] = summary[recent_mean_col]
    summary["heatwave_exposure_raw_p75"] = summary[recent_p75_col]
    summary["heatwave_exposure_raw_p90"] = summary[recent_p90_col]

    summary["heatwave_exposure_weight_mean_unclipped"] = relative_weight(
    summary["heatwave_exposure_raw_mean"]
    )

    summary["heatwave_exposure_weight_p75_unclipped"] = relative_weight(
    summary["heatwave_exposure_raw_p75"]
    )

    summary["heatwave_exposure_weight_p90_unclipped"] = relative_weight(
    summary["heatwave_exposure_raw_p90"]
    )

    summary["heatwave_exposure_weight_mean"] = attenuated_relative_weight(
    summary["heatwave_exposure_raw_mean"]
    )

    summary["heatwave_exposure_weight_p75"] = attenuated_relative_weight(
    summary["heatwave_exposure_raw_p75"]
    )

    summary["heatwave_exposure_weight_p90"] = attenuated_relative_weight(
    summary["heatwave_exposure_raw_p90"]
    )

    summary["heatwave_exposure_raw"] = summary["heatwave_exposure_raw_p75"]
    summary["heatwave_exposure_weight_unclipped"] = summary[
    "heatwave_exposure_weight_p75_unclipped"
    ]
    summary["heatwave_exposure_weight"] = summary["heatwave_exposure_weight_p75"]

    summary["heatwave_exposure_method"] = (
        f"TX >= {HOT_DAY_THRESHOLD_C}C, provincial p75 grid-cell hot days, "
        f"average {RECENT_START_YEAR}-{RECENT_END_YEAR}, relative to national mean, "
        f"attenuation={EXPOSURE_ATTENUATION}, clipped "
        f"{MIN_EXPOSURE_WEIGHT}-{MAX_EXPOSURE_WEIGHT}"
    )
    summary = summary.sort_values(
        "heatwave_exposure_weight",
        ascending=False,
    ).reset_index(drop=True)

    print("\nTop 15 provinces by official heatwave exposure weight:")
    print(
        summary[
            [
                "province_code",
                "province_name",
                "province_abbr",
                "heatwave_exposure_raw",
                "heatwave_exposure_weight",
                "heatwave_exposure_weight_mean",
                "heatwave_exposure_weight_p75",
                "heatwave_exposure_weight_p90",
            ]
        ].head(15)
    )

    return summary


def save_outputs(summary: pd.DataFrame, province_year: pd.DataFrame) -> None:
    print("\n=== Saving outputs ===")

    summary.to_csv(OUTPUT_SUMMARY_CSV, index=False, encoding="utf-8-sig")
    province_year.to_csv(OUTPUT_YEARLY_CSV, index=False, encoding="utf-8-sig")

    print(f"Saved summary indicators: {OUTPUT_SUMMARY_CSV}")
    print(f"Saved yearly indicators: {OUTPUT_YEARLY_CSV}")


def main() -> None:
    ds, provinces = load_inputs()

    grid_gdf = build_grid_points(ds)
    grid_mapping = assign_grid_points_to_provinces(grid_gdf, provinces)

    annual_hot_days_df = compute_annual_hot_days(ds)

    province_year = aggregate_to_provinces(
        annual_hot_days_df=annual_hot_days_df,
        grid_mapping=grid_mapping,
    )

    summary = compute_summary_indicators(province_year)

    save_outputs(summary, province_year)

    print("\n=== Done ===")
    print("Created provincial heatwave exposure indicators.")
    print("Official MVP exposure field: heatwave_exposure_weight")


if __name__ == "__main__":
    main()
