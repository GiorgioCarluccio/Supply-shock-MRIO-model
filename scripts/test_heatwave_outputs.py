import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.paths import CLIMATE_PROCESSED_DIR

file_path = CLIMATE_PROCESSED_DIR / "province_heatwave_indicators.csv"

df = pd.read_csv(file_path)

print("Rows:", len(df))
print("Missing province names:", df["province_name"].isna().sum())
print("Unique provinces:", df["province_code"].nunique())

print("\nTop 20 by heatwave exposure:")
print(
    df[
        [
            "province_code",
            "province_name",
            "province_abbr",
            "heatwave_exposure_raw",
            "heatwave_exposure_weight",
            "n_grid_cells",
        ]
    ].head(20)
)

print("\nBottom 20 by heatwave exposure:")
print(
    df[
        [
            "province_code",
            "province_name",
            "province_abbr",
            "heatwave_exposure_raw",
            "heatwave_exposure_weight",
            "n_grid_cells",
        ]
    ].tail(20)
)

print("\nGrid-cell coverage summary:")
print(df["n_grid_cells"].describe())
