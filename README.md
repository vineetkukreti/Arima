# ARIMA Product Forecasting

A forecasting system that predicts product demand using ARIMA models. It aggregates customer data at the product level and generates multi-year forecasts.

## What It Does

Takes historical sales data, groups it by product, and forecasts future demand. The system handles data validation, trains ARIMA models automatically, and outputs forecasts with performance metrics.

## Installation

Using uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

Or pip:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python -m src.models.product_customer_forecast --data data/your_data.xlsx

# With custom parameters
python -m src.models.product_customer_forecast \
    --data data/your_data.xlsx \
    --forecast-years 5 \
    --visualize
```

Or use the Python API:
```python
from src.models.product_customer_forecast import ProductCustomerForecaster, ForecastConfig

config = ForecastConfig(
    data_path='data/your_data.xlsx',
    forecast_years=3
)

forecaster = ProductCustomerForecaster(config)
forecaster.run()
results_df = forecaster.get_results_dataframe()
```

## Input Format

Your data file needs these columns:

| Column | Type | Description |
|--------|------|-------------|
| Year | int | Year of transaction |
| Product | string | Product identifier |
| CustomerID | string | Customer identifier |
| Quantity | int/float | Sales quantity |

Example:
```csv
Year,Product,CustomerID,Quantity
2020,Product_1,CUST_001,26
2020,Product_1,CUST_006,16
2021,Product_1,CUST_001,32
```

Common column name variations are automatically mapped (e.g., Time → Year).

## Output

Returns a DataFrame with forecasts:
```python
     Product  Num_Customers       Date  Forecast
0  Product_1             90 2025-01-01       842
1  Product_1             90 2026-01-01       842
```

Also generates JSON files with model metadata (parameters, error metrics, customer lists).

## Configuration

Key parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| data_path | Required | Path to data file |
| forecast_years | 3 | Years to forecast |
| min_observations | 5 | Min years needed |
| visualize | False | Create charts |
| parallel_processing | True | Use multiprocessing |
| num_workers | 15 | Worker threads |

## How It Works

The system uses `pmdarima.auto_arima` to automatically find the best ARIMA model for each product. It searches through different parameter combinations and picks the one with the lowest AIC score.

Common models:
- ARIMA(0,0,0) - Predicts the average (flat forecast)
- ARIMA(1,0,0) - Uses last value to predict next
- ARIMA(0,1,0) - Random walk with trend

Training uses 80% of data, validates on the remaining 20%, then forecasts future years.

## Data Validation

Automatically checks for:
- Missing values and duplicates
- Outliers (using IQR method)
- Time series gaps
- Zero or negative quantities

Warnings are logged but don't stop processing.

## Troubleshooting

**Getting flat forecasts?**
The model found no pattern in your data, so it predicts the mean. This is normal for data without trends.

**"No valid Product groups found"?**
Products need at least `min_observations` years of data. Try lowering this value.

**Running slow?**
Enable parallel processing: `--workers 15`, or filter to specific products: `--product Product_1`

## Project Structure

```
arima/
├── src/models/product_customer_forecast.py  # Main code
├── data/                                     # Input data
├── outputs/product_customer_forecasts/       # Results
│   ├── models/                              # Trained models
│   ├── metadata/                            # JSON metadata
│   └── visualizations/                      # Charts
└── forecast_notebook.ipynb                   # Interactive notebook
```

## Requirements

- Python 3.13+
- pandas
- statsmodels
- pmdarima

See `requirements.txt` for full list.
