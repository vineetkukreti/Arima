"""Synthetic data generator for ARIMA experiments.

This script derives realistic demand profiles from the historical
`ProductForecast.xlsx` source data and produces an extended synthetic dataset
with controllable trends, seasonality, and stochastic shocks.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = ROOT / "data" / "ProductForecast.xlsx"
OUTPUT_DIR = ROOT / "data" / "generated_data"
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
    df["Time"] = pd.PeriodIndex(df["Time"], freq="M")
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
    df["time_idx"] = (
        (df["Time"].dt.year - start.year) * 12
        + (df["Time"].dt.month - start.month)
    )

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
    seasonal_table: pd.DataFrame,
    periods: pd.PeriodIndex,
    rng: np.random.Generator,
) -> pd.DataFrame:
    seasonal_strength = 0.25 + 0.05 * (spec.item_category == 2)
    slope = spec.slope * rng.normal(1.0, 0.2)
    max_slope = 0.45 * spec.base_mean / len(periods)
    slope = float(np.clip(slope, -max_slope, max_slope))

    level = spec.base_mean * rng.uniform(0.92, 1.08)
    prev = level

    rows = []
    for idx, period in enumerate(periods):
        month = period.month
        trend = level + slope * idx
        season_factor = seasonal_table.loc[spec.item_code, month]
        seasonal = trend * (1 + seasonal_strength * (season_factor - 1))

        # Promotion lift during peak months (Nov/Dec) and sporadic campaign spikes.
        promo_lift = 0.0
        if month in {11, 12}:
            promo_lift += rng.normal(0.05, 0.02)
        if rng.random() < 0.035:
            promo_lift += rng.uniform(0.12, 0.32)

        baseline = seasonal * (1 + promo_lift)
        innovation = rng.normal(0.0, spec.noise_scale)
        value = baseline + 0.35 * (prev - seasonal) + innovation
        value = max(0.0, value)
        prev = value

        rows.append(
            {
                "Time": period.to_timestamp().strftime("%Y-%m"),
                "CUSTID": spec.cust_id,
                "ItemCode": spec.item_code,
                "ItemCategory": spec.item_category,
                "Number": int(round(value)),
            }
        )
    return pd.DataFrame(rows)


def build_dataset() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = _load_source()
    seasonal_table = _seasonality_table(df)
    specs = _series_specs(df)

    rng = np.random.default_rng(20241207)
    periods = pd.period_range("2019-01", "2024-12", freq="M")

    synthetic_frames = [
        _generate_series(spec, seasonal_table, periods, rng)
        for spec in specs.values()
    ]
    synthetic = pd.concat(synthetic_frames, ignore_index=True)
    synthetic.sort_values(["Time", "ItemCode", "CUSTID"], inplace=True)

    synthetic.to_csv(OUTPUT_FILE, index=False)

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
