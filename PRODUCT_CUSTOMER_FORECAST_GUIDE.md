# Product-Customer Forecasting Guide

## Overview

The `product_customer_forecast.py` script generates individual ARIMA or Prophet forecasting models for each unique Product-CustomerID combination in your dataset. This enables granular analysis of how each product performs for specific customers.

## Data Requirements

### Expected Columns

Your Excel or CSV file must contain these columns:

- **Year**: Year of the transaction (e.g., 2023)
- **Month**: Month of the transaction (1-12)
- **Product Category**: Product category classification (optional, not used in modeling)
- **Product**: Specific product identifier (e.g., "Product_A", "Widget_X")
- **CustomerID**: Customer identifier (e.g., "CUST_001", "12345")
- **Quantity**: Sales/demand quantity (numeric)

### Example Data Format

```
Year  Month  Product Category  Product     CustomerID  Quantity
2023  1      Electronics       Laptop_Pro  CUST_001    15
2023  1      Electronics       Mouse_X     CUST_001    50
2023  2      Electronics       Laptop_Pro  CUST_001    18
...
```

### Data Quality Requirements

- **Minimum observations**: Each Product-CustomerID combination needs at least 24 months of data (configurable via `--min-observations`)
- **Date continuity**: The script automatically fills missing months with 0 quantity
- **Aggregation**: Multiple transactions for the same Product-CustomerID-Month are summed

## Installation

Ensure all dependencies are installed:

```bash
pip install -r requirements.txt
```

For Prophet support (optional):

```bash
pip install prophet
```

## Usage

### Basic Usage

```bash
# Default: looks for data/RawData-Forecast-TBD2.xlsx
python -m src.models.product_customer_forecast
```

### Custom Data File

```bash
# Use existing ProductForecast.xlsx
python -m src.models.product_customer_forecast --data "data/ProductForecast.xlsx"

# Use CSV file
python -m src.models.product_customer_forecast --data "data/sales_data.csv"
```

### Configure Forecast Horizon

```bash
# Forecast 24 months instead of default 12
python -m src.models.product_customer_forecast --forecast-months 24

# Forecast 6 months
python -m src.models.product_customer_forecast --forecast-months 6
```

### Use Prophet Instead of ARIMA

```bash
python -m src.models.product_customer_forecast --model-type prophet
```

### Generate Visualizations

```bash
# Create plots for all Product-CustomerID combinations
python -m src.models.product_customer_forecast --visualize

# Combine multiple options
python -m src.models.product_customer_forecast \
  --data "data/ProductForecast.xlsx" \
  --forecast-months 18 \
  --visualize
```

### Adjust Minimum Observations

```bash
# Allow combinations with only 12 months of data
python -m src.models.product_customer_forecast --min-observations 12
```

## Output Structure

All outputs are saved to `outputs/product_customer_forecasts/`:

```
outputs/product_customer_forecasts/
├── consolidated_forecasts.xlsx    # Main Excel report
├── forecast_summary.csv           # Quick CSV summary
├── models/                        # Saved model files
│   ├── Product_A_CUST_001.pkl
│   ├── Product_A_CUST_002.pkl
│   └── ...
├── metadata/                      # Model metadata (JSON)
│   ├── Product_A_CUST_001.json
│   ├── Product_A_CUST_002.json
│   └── ...
└── visualizations/                # Forecast plots (if --visualize)
    ├── Product_A_CUST_001.png
    ├── Product_A_CUST_002.png
    └── ...
```

### Excel Report Contents

**consolidated_forecasts.xlsx** contains:

1. **Summary Sheet**: Overview of all models
   - Product
   - CustomerID
   - Model Type (ARIMA/Prophet)
   - ARIMA Order (if applicable)
   - RMSE, MAE, MAPE metrics
   - Success status
   - Error messages (if failed)

2. **All_Forecasts Sheet**: Detailed forecast data
   - Product
   - CustomerID
   - Date
   - Forecast value
   - Lower confidence interval
   - Upper confidence interval

### Model Files

- **PKL files**: Serialized trained models that can be reloaded for additional forecasting
- **JSON metadata**: Model parameters, metrics, and configuration

## Understanding the Output

### Performance Metrics

For each model, the script reports:

- **RMSE (Root Mean Squared Error)**: Average prediction error magnitude
- **MAE (Mean Absolute Error)**: Average absolute error
- **MAPE (Mean Absolute Percentage Error)**: Percentage-based error metric (best for comparison across different scales)

Lower values indicate better model performance.

### Forecast Confidence Intervals

Each forecast includes:
- **Forecast**: The predicted value
- **Lower_CI**: Lower bound of 95% confidence interval
- **Upper_CI**: Upper bound of 95% confidence interval

This shows the range where we expect the actual value to fall with 95% confidence.

## Advanced Usage

### Loading Saved Models

```python
import pickle
from pathlib import Path

# Load a specific model
model_path = Path('outputs/product_customer_forecasts/models/Product_A_CUST_001.pkl')
with open(model_path, 'rb') as f:
    model = pickle.load(f)

# Generate additional forecasts
new_forecast = model.forecast(steps=6)  # 6 more months
```

### Batch Processing Large Datasets

The script automatically processes all combinations sequentially with a progress bar. For very large datasets (thousands of combinations):

1. Consider filtering data before running
2. Use ARIMA instead of Prophet (faster)
3. Disable visualizations (`--visualize` off by default)

## Troubleshooting

### "No valid Product-CustomerID combinations found"

**Cause**: No combinations have enough observations

**Solution**: 
- Reduce `--min-observations` (e.g., `--min-observations 12`)
- Check your data has proper Year/Month/Product/CustomerID columns

### "Prophet not installed"

**Cause**: Prophet model requested but not installed

**Solution**:
```bash
pip install prophet
```

### Low Accuracy (High MAPE)

**Causes**:
- Insufficient historical data
- Highly irregular/volatile demand patterns
- Seasonal patterns not captured

**Solutions**:
- Collect more data
- Consider alternative forecasting methods for volatile products
- Review model parameters in metadata files

## Comparison: ARIMA vs Prophet

### Use ARIMA when:
- You have regular, predictable time series
- Faster execution needed
- Strong seasonal patterns with consistent frequency
- You need interpretable model parameters

### Use Prophet when:
- Handling missing data or outliers
- Multiple seasonal patterns
- Trend changes over time
- Less data preprocessing desired

## Example Workflow

1. **Prepare your data** in Excel with required columns
2. **Run initial analysis**:
   ```bash
   python -m src.models.product_customer_forecast --data "data/your_data.xlsx"
   ```
3. **Review results** in `consolidated_forecasts.xlsx`
4. **Identify best/worst performers** by sorting by MAPE
5. **Generate visualizations** for key combinations:
   ```bash
   python -m src.models.product_customer_forecast --data "data/your_data.xlsx" --visualize
   ```
6. **Use forecasts** for inventory planning, demand forecasting, or customer analysis

## Next Steps

- Integrate forecasts with optimization models (e.g., Gurobi for inventory optimization)
- Export forecasts to business intelligence tools
- Set up automated retraining pipelines
- Create dashboards from forecast results
