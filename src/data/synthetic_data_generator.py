"""Synthetic data generator for ARIMA experiments - Yearly Data

This utility generates synthetic yearly sales data for testing the ARIMA forecasting system.
The generated data simulates customer-item level transactions aggregated by year,
with realistic trend patterns and occasional growth spurts representing good/bad years.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
SOURCE_PATH = DATA_DIR / "ProductForecast.xlsx"
OUTPUT_DIR = DATA_DIR / "generated_data"
OUTPUT_FILE = OUTPUT_DIR / "synthetic_product_forecast.csv"
AGG_FILE = OUTPUT_DIR / "synthetic_item_demand.csv"


@dataclass
class SeriesSpec:
    """Container for customer-item level parameters."""

    cust_id: int
    item_code: int
    item_category: int
    base_mean: float
    slope: float
    noise_scale: float


def _load_source() -> pd.DataFrame:
    df = pd.read_excel(SOURCE_PATH)
    # Convert to yearly periods by extracting year from Time
    df["Time"] = pd.PeriodIndex(df["Time"], freq="Y")
    return df


def _seasonality_table(df: pd.DataFrame) -> pd.DataFrame:
    monthly = df.assign(month=df["Time"].dt.month)
    mean_by_item = monthly.groupby("ItemCode")["Number"].mean()
    seasonal = (
        monthly.groupby(["ItemCode", "month"])["Number"].mean()
        .unstack(fill_value=1.0)
        .div(mean_by_item, axis=0)
    )
    return seasonal


def _series_specs(df: pd.DataFrame) -> Dict[Tuple[int, int], SeriesSpec]:
    df = df.copy()
    start = df["Time"].min()
    # For yearly data, time index is just year difference
    df["time_idx"] = df["Time"].dt.year - start.year

    stats = {}
    grouped = df.groupby(["CUSTID", "ItemCode"])
    for (cust, item), group in grouped:
        x = group["time_idx"].to_numpy(dtype=float)
        y = group["Number"].to_numpy(dtype=float)
        if len(group) < 2:
            slope = 0.0
        else:
            slope, intercept = np.polyfit(x, y, deg=1)
        base_mean = float(y.mean())
        noise_scale = float(max(y.std(ddof=0) * 0.6, base_mean * 0.05))
        item_category = int(group["ITemCategory"].mode().iloc[0])
        stats[(cust, item)] = SeriesSpec(
            cust_id=int(cust),
            item_code=int(item),
            item_category=item_category,
            base_mean=base_mean,
            slope=float(slope),
            noise_scale=noise_scale,
        )
    return stats


def _generate_series(
    spec: SeriesSpec,
    periods: pd.PeriodIndex,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Generate yearly time series for a customer-item combination."""
    slope = spec.slope * rng.normal(1.0, 0.2)
    max_slope = 0.45 * spec.base_mean / len(periods)
    slope = float(np.clip(slope, -max_slope, max_slope))

    level = spec.base_mean * rng.uniform(0.92, 1.08)
    prev = level

    rows = []
    for idx, period in enumerate(periods):
        # Simple trend with noise for yearly data
        trend = level + slope * idx

        # Add occasional growth spurts (representing good years)
        growth_boost = 0.0
        if rng.random() < 0.15:  # 15% chance of a good year
            growth_boost = rng.uniform(0.10, 0.25)

        baseline = trend * (1 + growth_boost)
        innovation = rng.normal(0.0, spec.noise_scale)
        value = baseline + 0.35 * (prev - trend) + innovation
        value = max(0.0, value)
        prev = value

        rows.append(
            {
                "Time": str(period.year),  # Just the year as string
                "CUSTID": spec.cust_id,
                "ItemCode": spec.item_code,
                "ItemCategory": spec.item_category,
                "Number": int(round(value)),
            }
        )
    return pd.DataFrame(rows)


def build_dataset() -> None:
    """Generate synthetic yearly dataset."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = _load_source()
    # No seasonality table needed for yearly data
    specs = _series_specs(df)

    rng = np.random.default_rng(20241207)
    # Generate yearly data from 2019 to 2024
    periods = pd.period_range("2019", "2024", freq="Y")

    synthetic_frames = [
        _generate_series(spec, periods, rng)
        for spec in specs.values()
    ]
    synthetic = pd.concat(synthetic_frames, ignore_index=True)
    synthetic.sort_values(["Time", "ItemCode", "CUSTID"], inplace=True)

    synthetic.to_csv(OUTPUT_FILE, index=False)

    # Aggregate by year for item demand
    aggregated = (
        synthetic.groupby(["Time", "ItemCode", "ItemCategory"], as_index=False)["Number"]
        .sum()
        .rename(columns={"Number": "TotalNumber"})
    )
    aggregated.to_csv(AGG_FILE, index=False)


if __name__ == "__main__":
    build_dataset()
    print(f"Synthetic dataset written to {OUTPUT_FILE}")
    print(f"Aggregated item demand written to {AGG_FILE}")
