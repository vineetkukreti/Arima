"""ARIMA Product Forecasting Script
==================================

Production-ready ARIMA forecasting for product demand/sales data. The module
lives under ``src/models`` to keep forecasting algorithms together and make it
simpler to add optimisers (for example, ``gurobipy`` models) later on.

Usage:
    python -m src.models.arima_forecast

The script will:
1. Load data from data/generated_data/synthetic_product_forecast.csv
2. Aggregate by time period
3. Test for stationarity
4. Find optimal ARIMA parameters
5. Generate 60-month forecast
6. Export results to outputs/

Author: ARIMA Forecasting System
Date: 2025-12-07
"""

from __future__ import annotations

import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pmdarima import auto_arima
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "generated_data" / "synthetic_product_forecast.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
VIZ_DIR = OUTPUT_DIR / "visualizations"
FORECAST_STEPS = 60  # 60 months (5 years)


def ensure_directories() -> None:
    """Create output directories if they don't exist."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VIZ_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Output directories ready: {OUTPUT_DIR}, {VIZ_DIR}")


def load_and_aggregate_data(file_path: Path) -> pd.DataFrame:
    """Load data, aggregate by time period, and enforce MS frequency."""

    print(f"\nLoading data from: {file_path}")
    if file_path.suffix == ".csv":
        df_raw = pd.read_csv(file_path)
    else:
        df_raw = pd.read_excel(file_path) # reading the excel file 
    print(f"✓ Loaded {df_raw.shape[0]} records")

    # # 20 columns
    # l = ['item_code ','custId','Time','Number','Number of Sales']
    # df_raw = df_raw[l]

    cust_id = 234
    item_code = 123 

    cust_id = 232
    item_code = 123 
    
    unique_cust_id = df_raw['custId'].unique()
    unique_item_code = df_raw['item_code'].unique()
    
    for ci in df_raw['custId'].unique():
        for item in df_raw['item_code'].unique():
            df = df_raw[(df_raw['custId'] == ci) & (df_raw['item_code'] == item)]

            df.to_csv(f"data/generated_data/{ci}_{item}.csv", index=False)




    ### 

    df_ts = df_raw.groupby("Time")["Number"].sum().reset_index()
    df_ts.columns = ["Date", "Total_Number"]

    df_ts["Date"] = pd.to_datetime(df_ts["Date"], format="%Y-%m")
    df_ts.set_index("Date", inplace=True)
    df_ts = df_ts.asfreq("MS")

    print(f"✓ Aggregated to {len(df_ts)} time periods")
    print(
        "  Date range: "
        f"{df_ts.index.min().strftime('%Y-%m')} to {df_ts.index.max().strftime('%Y-%m')}"
    )

    return df_ts


def adf_test(timeseries: pd.Series, title: str = "") -> bool:
    """Perform Augmented Dickey-Fuller test for stationarity."""

    result = adfuller(timeseries.dropna(), autolag="AIC")

    print(f"\nADF Test - {title}:")
    print(f"  ADF Statistic: {result[0]:.4f}")
    print(f"  p-value: {result[1]:.4f}")

    if result[1] <= 0.05:
        print("  ✓ Series is STATIONARY (p-value <= 0.05)")
        return True
    print("  ✗ Series is NON-STATIONARY (p-value > 0.05)")
    return False


def find_optimal_arima(train_data: pd.Series) -> Tuple[Tuple[int, int, int], Tuple[int, int, int, int]]:
    """Find optimal ARIMA parameters using auto_arima."""

    print("\nFinding optimal ARIMA parameters...")

    auto_model = auto_arima(
        train_data,
        start_p=0,
        start_q=0,
        max_p=5,
        max_q=5,
        d=None,
        D=1,
        seasonal=True,
        m=12,
        stepwise=True,
        suppress_warnings=True,
        error_action="ignore",
        trace=False,
    )

    best_order = auto_model.order
    seasonal_order = auto_model.seasonal_order
    print(f"✓ Best ARIMA order found: {best_order}")
    print(f"  Seasonal Order: {seasonal_order}")
    print(f"  AIC: {auto_model.aic():.2f}")

    return best_order, seasonal_order


def train_and_evaluate(
    train: pd.Series,
    test: pd.Series,
    order: Tuple[int, int, int],
    seasonal_order: Tuple[int, int, int, int],
) -> Tuple[Dict[str, float], ARIMA]:
    """Train ARIMA model and evaluate on test set."""

    print(f"\nTraining ARIMA{order}x{seasonal_order} model...")

    model = ARIMA(train, order=order, seasonal_order=seasonal_order)
    fitted_model = model.fit()

    predictions = fitted_model.forecast(steps=len(test))

    mse = mean_squared_error(test, predictions)
    rmse = float(np.sqrt(mse))
    mae_val = mean_absolute_error(test, predictions)
    mape = float(np.mean(np.abs((test - predictions) / test)) * 100)

    metrics = {"MSE": float(mse), "RMSE": rmse, "MAE": float(mae_val), "MAPE": mape}

    print("✓ Model trained successfully")
    print(f"  RMSE: {rmse:.2f}")
    print(f"  MAPE: {mape:.2f}%")

    return metrics, fitted_model


def generate_forecast(
    full_data: pd.Series,
    order: Tuple[int, int, int],
    seasonal_order: Tuple[int, int, int, int],
    steps: int,
) -> Tuple[pd.DataFrame, ARIMA]:
    """Generate future forecast using the full dataset."""

    print(f"\nGenerating {steps}-month forecast...")

    model = ARIMA(full_data, order=order, seasonal_order=seasonal_order)
    fitted_model = model.fit()

    forecast_result = fitted_model.get_forecast(steps=steps)
    forecast_values = forecast_result.predicted_mean
    forecast_ci = forecast_result.conf_int(alpha=0.05)

    forecast_dates = pd.date_range(
        start=full_data.index[-1] + pd.DateOffset(months=1),
        periods=steps,
        freq="MS",
    )

    forecast_df = pd.DataFrame(
        {
            "Date": forecast_dates,
            "Forecast": forecast_values.values,
            "Lower_CI_95": forecast_ci.iloc[:, 0].values,
            "Upper_CI_95": forecast_ci.iloc[:, 1].values,
        }
    )
    forecast_df.set_index("Date", inplace=True)

    print("✓ Forecast generated")
    print(
        "  Period: "
        f"{forecast_df.index.min().strftime('%Y-%m')} to {forecast_df.index.max().strftime('%Y-%m')}"
    )

    return forecast_df, fitted_model


def create_forecast_plot(
    historical: pd.Series,
    forecast: pd.DataFrame,
    output_path: Path,
) -> None:
    """Create and save forecast visualization."""

    plt.figure(figsize=(16, 7))

    plt.plot(historical.index, historical, label="Historical Data", linewidth=2.5, color="blue")
    plt.plot(
        forecast.index,
        forecast["Forecast"],
        label="Forecast",
        linewidth=2.5,
        color="red",
        linestyle="--",
    )

    plt.fill_between(
        forecast.index,
        forecast["Lower_CI_95"],
        forecast["Upper_CI_95"],
        alpha=0.3,
        color="red",
        label="95% Confidence Interval",
    )

    plt.axvline(x=historical.index[-1], color="green", linestyle=":", linewidth=2, label="Forecast Start")

    plt.title("ARIMA Product Forecast - 60 Month Projection", fontsize=16, fontweight="bold")
    plt.xlabel("Date", fontsize=13)
    plt.ylabel("Total Number", fontsize=13)
    plt.legend(loc="best", fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"✓ Forecast plot saved to: {output_path}")


def export_results(
    historical: pd.DataFrame,
    forecast: pd.DataFrame,
    metrics: Dict[str, float],
    order: Tuple[int, int, int],
    seasonal_order: Tuple[int, int, int, int],
    output_dir: Path,
) -> None:
    """Export results to Excel and CSV."""

    diagnostics_data = {
        "Metric": [
            "ARIMA Order",
            "Seasonal Order",
            "RMSE (Test)",
            "MAE (Test)",
            "MAPE (Test)",
            "Forecast Horizon",
            "Generated On",
        ],
        "Value": [
            str(order),
            str(seasonal_order),
            f"{metrics['RMSE']:.2f}",
            f"{metrics['MAE']:.2f}",
            f"{metrics['MAPE']:.2f}%",
            f"{len(forecast)} months",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ],
    }
    diagnostics_df = pd.DataFrame(diagnostics_data)

    excel_path = output_dir / "forecast_results.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        historical.to_excel(writer, sheet_name="Historical_Data")
        forecast.to_excel(writer, sheet_name="Forecast")
        diagnostics_df.to_excel(writer, sheet_name="Model_Diagnostics", index=False)

    print(f"✓ Results exported to: {excel_path}")

    csv_path = output_dir / "forecast_results.csv"
    forecast.to_csv(csv_path)
    print(f"✓ Forecast CSV saved to: {csv_path}")


def main() -> None:
    """Main execution function."""

    print("=" * 70)
    print("ARIMA PRODUCT FORECASTING SYSTEM")
    print("=" * 70)

    ensure_directories()

    df_ts = load_and_aggregate_data(DATA_PATH)

    is_stationary = adf_test(df_ts["Total_Number"], title="Original Series")
    _ = is_stationary  # Stationarity report is printed; flag kept for future use.

    train_size = int(len(df_ts) * 0.8)
    train = df_ts["Total_Number"][:train_size]
    test = df_ts["Total_Number"][train_size:]
    print("\nTrain-Test Split:")
    print(f"  Training: {len(train)} months")
    print(f"  Testing: {len(test)} months")

    best_order, seasonal_order = find_optimal_arima(train)

    metrics, _ = train_and_evaluate(train, test, best_order, seasonal_order)

    forecast_df, final_model = generate_forecast(
        df_ts["Total_Number"],
        best_order,
        seasonal_order,
        FORECAST_STEPS,
    )
    _ = final_model

    plot_path = VIZ_DIR / "forecast_final.png"
    create_forecast_plot(df_ts["Total_Number"], forecast_df, plot_path)

    export_results(df_ts[["Total_Number"]], forecast_df, metrics, best_order, seasonal_order, OUTPUT_DIR)

    print("\n" + "=" * 70)
    print("FORECAST SUMMARY")
    print("=" * 70)
    print(f"Model: ARIMA{best_order}x{seasonal_order}")
    print(f"Test MAPE: {metrics['MAPE']:.2f}%")
    print(
        f"Forecast Period: {forecast_df.index.min().strftime('%b %Y')} - "
        f"{forecast_df.index.max().strftime('%b %Y')}"
    )
    print(f"Average Forecast: {forecast_df['Forecast'].mean():.0f}")
    print(f"Forecast Range: {forecast_df['Forecast'].min():.0f} - {forecast_df['Forecast'].max():.0f}")
    print("=" * 70)
    print("\n✓ ANALYSIS COMPLETE!")
    print(f"\nResults saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
