# Product-Customer-Category ARIMA Forecasting System

Time series forecasting system for product demand using ARIMA models with 3-way grouping by Product × Customer × Category.

## Features

- ✅ **3-way grouping**: Product × CustomerID × Product Category
- ✅ **Multiple aggregation modes**: Monthly (default) or Yearly
- ✅ **Parallel processing**: Speed up with multi-core processing
- ✅ **Clean outputs**: Non-negative integer forecasts only (no decimals, no scientific notation)
- ✅ **Comprehensive exports**: Excel, CSV, visualizations, and model files

## Quick Start

### Installation

```bash
# Install dependencies
uv pip install -r requirements.txt
```

### Basic Usage

```bash
# Run with your data
uv run python -m src.models.product_customer_forecast \
  --data "data/your_file.xlsx" \
  --forecast-months 36 \
  --aggregation monthly
```

### With Parallel Processing (Default - Recommended for large datasets)

```bash
# Parallel processing is enabled by default
uv run python -m src.models.product_customer_forecast \
  --data "data/your_file.xlsx" \
  --forecast-months 36 \
  --workers 8 \
  --aggregation monthly

# To disable parallel processing, use --no-parallel
uv run python -m src.models.product_customer_forecast \
  --data "data/your_file.xlsx" \
  --no-parallel
```

## Data Requirements

Your Excel/CSV file must contain these columns:

- `Year`: Year of transaction (e.g., 2023)
- `Month`: Month of transaction (1-12)
- `Product Category`: Category classification (e.g., "Electronics")
- `Product`: Product identifier (e.g., "Product_A")
- `CustomerID`: Customer identifier (e.g., "CUST_001")
- `Quantity`: Sales/demand quantity (numeric)

## Command Line Options

```
--data PATH                     Path to Excel/CSV data file
--forecast-months N             Number of months to forecast (default: 36)
--min-observations N            Minimum data points required (default: 24)
--aggregation {monthly,yearly}  Time aggregation mode (default: monthly)
--no-parallel                   Disable parallel processing (enabled by default)
--workers N                     Number of parallel workers (default: CPU-1)
--visualize                     Generate forecast plots
--model-type {arima,prophet}    Model type (default: arima)
```

## Output Files

Results saved to `outputs/product_customer_forecasts/`:

- `consolidated_forecasts.xlsx` - All forecasts and summary
- `forecast_summary.csv` - Quick CSV summary
- `models/*.pkl` - Trained models for each combination
- `metadata/*.json` - Model parameters and metrics
- `visualizations/*.png` - Forecast plots (if --visualize enabled)

## Performance

For large datasets (2000+ combinations):
- **Sequential**: ~4 hours
- **Parallel (8 workers)**: ~30-40 minutes
- **Speedup**: ~6-8x faster

## Example

```bash
# Generate test data
python create_test_data.py

# Run forecast (parallel processing enabled by default)
uv run python -m src.models.product_customer_forecast \
  --data "data/test_forecast_data.xlsx" \
  --forecast-months 6 \
  --workers 4 \
  --visualize
```

## Output Format

All forecast values are guaranteed to be:
- ✅ Non-negative (minimum: 0)
- ✅ Integers only (no decimals)
- ✅ No scientific notation

## Documentation

See `PRODUCT_CUSTOMER_FORECAST_GUIDE.md` for detailed usage guide.

## Requirements

- Python 3.10+
- See `requirements.txt` for dependencies

## License

Internal use only.
