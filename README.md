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

### Option 1: Using Data Files (Command Line)

```bash
python -m src.models.product_customer_forecast --data data/your_data.xlsx

# With custom parameters
python -m src.models.product_customer_forecast \
    --data data/your_data.xlsx \
    --forecast-years 5 \
    --visualize
```

### Option 2: Using Data Files (Python API)

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

### Option 3: ERP Integration (Python API)

For ERP integration, use a DataFrame instead of a file path:

```python
from src.models.product_customer_forecast import ProductCustomerForecaster, ForecastConfig
import pandas as pd

# Import data from ERP (client implements this function)
def ImportFromErp():
    """
    Client-implemented function to fetch data from ERP system.
    Should return a DataFrame with columns: Year, Product, CustomerID, Quantity
    
    Example implementation (replace with actual ERP logic):
    """
    # TODO: Replace with actual ERP API call/database query
    return pd.read_excel('data/erp_export.xlsx')

# Get data from ERP
erp_data = ImportFromErp()

# Configure forecaster with DataFrame (not file path)
config = ForecastConfig(
    data_path=None,           # Set to None when using dataframe
    dataframe=erp_data,       # Pass ERP data directly
    forecast_years=3
)

# Run forecasting
forecaster = ProductCustomerForecaster(config)
forecaster.run()

# Get results
results_df = forecaster.get_results_dataframe()

# Export results back to ERP (client implements this function)
def ExportToErp(results_df):
    """
    Client-implemented function to send forecast results to ERP system.
    
    Args:
        results_df: DataFrame with columns [Product, Num_Customers, Date, Forecast]
    
    Example implementation (replace with actual ERP logic):
    """
    # TODO: Replace with actual ERP API call/database insert
    print(f"Exporting {len(results_df)} forecast records to ERP...")
    # results_df.to_sql('forecasts', erp_connection)
    pass

# Send results back to ERP
ExportToErp(results_df)
```

**Note:** The system ensures only ONE data source is used at a time:
- If `data_path` is provided → loads from file
- If `dataframe` is provided (and `data_path` is None) → uses the dataframe
- Both cannot be used simultaneously

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

### In-Memory Results

Get forecasts as a DataFrame (no files created):
```python
results_df = forecaster.get_results_dataframe()

# DataFrame structure:
     Product  Num_Customers       Date  Forecast
0  Product_1             90 2025-01-01       842
1  Product_1             90 2026-01-01       842
```

### Export Options

#### 1. Export to Local Files (Excel/CSV)

Use `export_results()` for local file exports:
```python
forecaster.export_results()

# Creates:
# - outputs/product_customer_forecasts/consolidated_forecasts.xlsx
# - outputs/product_customer_forecasts/forecast_summary.csv
```

#### 2. Export to ERP System

Use the client-implemented `ExportToErp()` function:
```python
ExportToErp(results_df)  # Client implements this function
```

### Metadata Files

The system automatically generates JSON files with model metadata for each product:
- Model parameters (ARIMA order, seasonal order)
- Performance metrics (RMSE, MAE, MAPE)
- Customer lists
- Forecast configuration

Location: `outputs/product_customer_forecasts/metadata/`

## Configuration

Key parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| data_path | None | Path to data file (use this OR dataframe, not both) |
| dataframe | None | Pandas DataFrame (use this OR data_path, not both) |
| forecast_years | 3 | Years to forecast |
| min_observations | 5 | Min years needed |
| visualize | False | Create charts |
| parallel_processing | True | Use multiprocessing |
| num_workers | 15 | Worker threads |

**Note:** Either `data_path` or `dataframe` must be provided. If both are provided, `data_path` takes priority.

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

## ERP Integration

The forecasting system supports integration with ERP systems through two client-implemented functions: `ImportFromErp()` and `ExportToErp()`. These are **placeholder functions** that clients should implement according to their ERP system's requirements.

### ImportFromErp() - Data Import

**Purpose:** Fetch historical sales data from your ERP system.

**Implementation Requirements:**
- Must return a pandas DataFrame
- Required columns: `Year`, `Product`, `CustomerID`, `Quantity`
- Optional columns: `Month`, `Product Category`

**Example Implementation:**
```python
def ImportFromErp():
    """
    Fetch data from ERP system.
    Replace this with your actual ERP integration logic.
    """
    # Option 1: Database query
    import sqlalchemy
    engine = sqlalchemy.create_engine('your_erp_connection_string')
    query = """
        SELECT 
            YEAR(OrderDate) as Year,
            ProductCode as Product,
            CustomerCode as CustomerID,
            SUM(Quantity) as Quantity
        FROM SalesOrders
        WHERE OrderDate >= '2020-01-01'
        GROUP BY YEAR(OrderDate), ProductCode, CustomerCode
    """
    return pd.read_sql(query, engine)
    
    # Option 2: API call
    # response = requests.get('https://erp.example.com/api/sales')
    # return pd.DataFrame(response.json())
    
    # Option 3: File export from ERP
    # return pd.read_excel('erp_export.xlsx')
```

### ExportToErp() - Results Export

**Purpose:** Send forecast results back to your ERP system.

**Input:** DataFrame with columns:
- `Product`: Product identifier
- `Num_Customers`: Number of customers for this product
- `Date`: Forecast date (datetime)
- `Forecast`: Forecasted quantity (integer)

**Example Implementation:**
```python
def ExportToErp(results_df):
    """
    Send forecast results to ERP system.
    Replace this with your actual ERP integration logic.
    """
    # Option 1: Database insert
    import sqlalchemy
    engine = sqlalchemy.create_engine('your_erp_connection_string')
    results_df.to_sql('ForecastResults', engine, if_exists='append', index=False)
    print(f"✓ Exported {len(results_df)} records to ERP database")
    
    # Option 2: API call
    # import requests
    # payload = results_df.to_dict('records')
    # response = requests.post('https://erp.example.com/api/forecasts', json=payload)
    # print(f"✓ API response: {response.status_code}")
    
    # Option 3: File export for ERP import
    # results_df.to_excel('forecast_for_erp.xlsx', index=False)
    # print(f"✓ Created forecast_for_erp.xlsx for ERP import")
```

### Sample Implementations

See `forecast_notebook.ipynb` for working examples of both functions. The notebook includes:
- Sample `ImportFromErp()` that reads from a local file
- Sample `ExportToErp()` that prints results
- Complete workflow from ERP data → forecasting → ERP export

**Note:** These are demonstration functions. Clients should replace them with actual ERP integration code.

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
