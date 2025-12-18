# Forecasting & Optimization System

A comprehensive forecasting and optimization platform supporting multiple modeling approaches:
- **ARIMA**: Statistical time series forecasting for demand prediction
- **Gurobi**: Mathematical optimization for demand planning and resource allocation

## 📊 Project Overview

This project provides production-ready implementations for:
- **ARIMA Forecasting**: Predict product demand/sales for the next 60 months using AutoRegressive Integrated Moving Average models
- **Gurobi Optimization**: Solve demand planning problems with production scheduling, inventory management, and cost minimization (requires Gurobi license)
- Comprehensive data preprocessing and synthetic data generation
- Automated model selection and parameter tuning
- Professional visualizations and reporting

## 📁 Project Structure

```
arima/
├── data/
│   ├── ProductForecast.xlsx              # Source data
│   └── generated_data/                   # Synthetic datasets
│       ├── synthetic_product_forecast.csv
│       └── synthetic_item_demand.csv
├── src/
│   ├── __init__.py                       # Package initialization
│   ├── models/                           # Forecasting & optimization models
│   │   ├── __init__.py
│   │   ├── arima_forecast.py            # ARIMA time series forecasting
│   │   └── gurobi_optimizer.py          # Gurobi optimization workflows
│   └── data/                             # Data utilities
│       ├── __init__.py
│       └── synthetic_data_generator.py  # Synthetic data generation
├── notebooks/
│   ├── 01_data_exploration.ipynb         # EDA and analysis
│   └── 02_arima_modeling.ipynb           # Interactive modeling
├── outputs/
│   ├── forecast_results.xlsx             # ARIMA forecast (Excel)
│   ├── forecast_results.csv              # ARIMA forecast (CSV)
│   ├── optimization_results.csv          # Gurobi results
│   └── visualizations/                   # Generated plots
│       └── forecast_final.png
├── main.py                               # CLI entry point
├── requirements.txt                      # Python dependencies
├── pyproject.toml                        # Project metadata
└── README.md                             # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.13+ (or 3.8+)
- pip package manager
- **Optional**: Gurobi license (for optimization features)

### Installation

1. **Navigate to the project directory:**
   ```bash
   cd /home/vineet/Desktop/projects/arima
   ```

2. **Create and activate virtual environment (recommended):**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install required packages:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Optional - Install Gurobi (for optimization):**
   ```bash
   pip install gurobipy
   # Obtain free academic license at: https://www.gurobi.com/downloads/
   ```

### Usage

#### Command Line Interface (Main Entry Point)

**Run ARIMA Forecasting (Default):**
```bash
python main.py
# or explicitly:
python main.py --model arima
```

**Run Gurobi Optimization:**
```bash
python main.py --model gurobi
```

**Help:**
```bash
python main.py --help
```

#### Direct Module Execution

**ARIMA Forecasting:**
```bash
python -m src.models.arima_forecast
```

**Gurobi Optimization:**
```bash
python -m src.models.gurobi_optimizer
```

**Generate Synthetic Data:**
```bash
python -m src.data.synthetic_data_generator
```

#### Jupyter Notebooks (Interactive Exploration)

1. **Start Jupyter:**
   ```bash
   jupyter notebook
   ```

2. **Run notebooks in order:**
   - `notebooks/01_data_exploration.ipynb` - Data exploration and EDA
   - `notebooks/02_arima_modeling.ipynb` - Complete ARIMA modeling and forecasting

## 📈 Data Description

**Source File**: `data/ProductForecast.xlsx`

**Columns**:
- `Time`: Monthly time periods (format: YYYY-MM)
- `CUSTID`: Customer identifier
- `ItemCode`: Product code
- `ITemCategory`: Product category
- `Number`: Quantity/demand value (target variable)

**Approach**: The system aggregates `Number` values across all customers and products to create a single monthly time series for forecasting.

## 🔬 Methodology

### ARIMA Time Series Forecasting

### 1. Data Preprocessing
- Load Excel/CSV data
- Aggregate by time period (monthly)
- Handle missing values via interpolation
- Set proper datetime index with monthly frequency

### 2. Exploratory Data Analysis
- Time series visualization
- Seasonal decomposition (trend, seasonality, residual)
- Distribution analysis
- Rolling statistics

### 3. Stationarity Testing
- Augmented Dickey-Fuller (ADF) test
- First-order differencing if non-stationary
- Validation of stationarity after transformation

### 4. Model Development
- ACF/PACF analysis for parameter hints
- Auto ARIMA for optimal (p, d, q) selection
- Train-test split (80-20) for validation
- Model fitting with statsmodels ARIMA

### 5. Model Evaluation
- Performance metrics: RMSE, MAE, MAPE
- Residual diagnostics (normality, autocorrelation)
- Ljung-Box test for residual independence
- Q-Q plots and ACF of residuals

### 6. Forecasting
- Retrain on full dataset
- Generate 60-month forecast
- Calculate 95% confidence intervals
- Comprehensive visualization

### Gurobi Optimization

The optimization module provides a framework for:
- **Production Planning**: Determine optimal production quantities
- **Inventory Management**: Balance holding costs with demand fulfillment
- **Cost Minimization**: Minimize total system costs (production + inventory)
- **Constraint Satisfaction**: Meet demand while respecting capacity limits

**Key Components:**
- Decision variables: Production and inventory levels per period
- Objective function: Minimize total cost
- Constraints: Inventory balance, demand satisfaction, capacity limits
- Solver: Gurobi MIP/LP solver

## 📊 Output Files

### Excel Output (`outputs/forecast_results.xlsx`)

**Sheet 1 - Historical_Data**: Original time series data

**Sheet 2 - Forecast**: 
- Date
- Forecast value
- Lower confidence interval (95%)
- Upper confidence interval (95%)

**Sheet 3 - Model_Diagnostics**:
- ARIMA order (p, d, q)
- Model performance metrics
- AIC/BIC scores
- Training/test set sizes

### CSV Output (`outputs/forecast_results.csv`)
Forecast data in CSV format for easy integration with other tools.

### Visualizations (`outputs/visualizations/`)
- **01_timeseries_overview.png**: Complete historical view
- **02_decomposition.png**: Trend, seasonal, and residual components
- **03_stationarity_tests.png**: Original vs differenced series
- **04_acf_pacf.png**: Autocorrelation analysis
- **05_residual_diagnostics.png**: Residual validation plots
- **06_forecast_plot.png**: Final forecast with confidence intervals
- **07_train_test_validation.png**: Model validation performance

## 📋 Key Performance Metrics

The system evaluates model performance using:

- **RMSE** (Root Mean Squared Error): Overall prediction accuracy
- **MAE** (Mean Absolute Error): Average prediction error
- **MAPE** (Mean Absolute Percentage Error): Percentage-based accuracy
- **AIC/BIC**: Model selection criteria (lower is better)

Target: MAPE < 20% for acceptable forecast quality

## 💡 Business Insights

The forecasts provide actionable insights for:
- **Inventory Planning**: Optimize stock levels based on predicted demand
- **Resource Allocation**: Plan production and staffing needs
- **Budget Forecasting**: Estimate future revenue and costs
- **Risk Management**: Use confidence intervals for scenario planning
- **Trend Analysis**: Identify long-term demand patterns

## 🔧 Customization

### ARIMA Forecasting

**Changing Forecast Horizon:**

In `src/models/arima_forecast.py`:
```python
FORECAST_STEPS = 60  # Change to desired number of months
```

**Adjusting Train-Test Split:**
```python
train_size = int(len(df_ts) * 0.8)  # Change 0.8 to desired ratio
```

**Enabling Seasonal ARIMA:**

In `auto_arima()` call:
```python
auto_model = auto_arima(
    train,
    seasonal=True,      # Enable seasonality
    m=12,               # Seasonal period (12 for monthly data)
    ...
)
```

### Gurobi Optimization

**Customizing Optimization Model:**

Edit `src/models/gurobi_optimizer.py` to:
- Add new decision variables (e.g., transportation, workforce)
- Include additional constraints (capacity, budget, service levels)
- Modify objective function (maximize profit, minimize lead time)
- Extend to multi-product or multi-location scenarios

**Example: Adding Capacity Constraints:**
```python
# In build_optimization_model():
max_capacity = 5000  # units per period
for t in range(forecast_periods):
    model.addConstr(production[t] <= max_capacity, f"capacity_{t}")
```

## 📚 Dependencies

### Core Packages
- `pandas>=2.0.0`: Data manipulation and analysis
- `numpy>=1.24.0`: Numerical operations
- `matplotlib>=3.7.0`, `seaborn>=0.12.0`: Visualization
- `statsmodels>=0.14.0`: ARIMA modeling and statistical tests
- `pmdarima>=2.0.0`: Auto ARIMA parameter selection
- `scipy>=1.10.0`, `sklearn`: Statistical analysis and metrics
- `openpyxl>=3.1.0`: Excel file handling

### Optional (Optimization)
- `gurobipy>=11.0.0`: Mathematical optimization solver (requires license)

### Development
- `jupyter>=1.0.0`, `notebook>=6.5.0`: Interactive notebooks

See `requirements.txt` for complete list with versions.

## 🐛 Troubleshooting

### Installation Issues
```bash
# If pmdarima installation fails, try:
pip install pmdarima --no-build-isolation

# For openpyxl issues:
pip install --upgrade openpyxl
```

### Gurobi License Issues
```bash
# Check if Gurobi is installed and licensed:
python -c "import gurobipy; print(gurobipy.gurobi.version())"

# Academic/Free license: https://www.gurobi.com/downloads/
# The free license allows models up to 2000 variables/constraints
```

### Jupyter Notebook Not Found
```bash
# Verify jupyter is installed:
pip install --upgrade jupyter notebook
```

### Data Loading Errors
- Ensure `ProductForecast.xlsx` or synthetic data is in `data/` directory
- Check that file paths are correct in scripts
- Verify CSV format matches expected columns

