# ARIMA Product Forecasting System

A comprehensive time series forecasting system using ARIMA (AutoRegressive Integrated Moving Average) to predict product demand/sales for the next 36-60 months.

## 📊 Project Overview

This project implements an end-to-end ARIMA forecasting pipeline that:
- Loads and aggregates product forecast data from Excel
- Performs exploratory data analysis (EDA)
- Tests for stationarity and applies transformations
- Automatically determines optimal ARIMA parameters
- Trains and validates the forecasting model
- Generates 36-60 month future predictions with confidence intervals
- Exports results to Excel/CSV with visualizations

## 📁 Project Structure

```
arima/
├── data/
│   └── ProductForecast.xlsx          # Source data
├── notebooks/
│   ├── 01_data_exploration.ipynb     # EDA and data analysis
│   └── 02_arima_modeling.ipynb       # Model development and forecasting
├── src/
│   └── arima_forecast.py             # Production script
├── outputs/
│   ├── forecast_results.xlsx         # Forecast results (Excel)
│   ├── forecast_results.csv          # Forecast results (CSV)
│   ├── cleaned_timeseries.csv        # Processed data
│   └── visualizations/               # All generated plots
│       ├── 01_timeseries_overview.png
│       ├── 02_decomposition.png
│       ├── 03_stationarity_tests.png
│       ├── 04_acf_pacf.png
│       ├── 05_residual_diagnostics.png
│       ├── 06_forecast_plot.png
│       └── 07_train_test_validation.png
├── requirements.txt                  # Python dependencies
└── README.md                         # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd /home/vineet/Desktop/projects/arima
   ```

2. **Install required packages:**
   ```bash
   pip install -r requirements.txt
   ```

### Usage

#### Option 1: Using Jupyter Notebooks (Recommended for exploration)

1. **Start Jupyter:**
   ```bash
   jupyter notebook
   ```

2. **Run notebooks in order:**
   - `notebooks/01_data_exploration.ipynb` - Data exploration and EDA
   - `notebooks/02_arima_modeling.ipynb` - Complete ARIMA modeling and forecasting

#### Option 2: Using Python Script (Automated)

Run the production script for automated forecasting:
```bash
cd src
python arima_forecast.py
```

This will:
- Load and process the data
- Find optimal ARIMA parameters
- Generate 60-month forecast
- Create visualizations
- Export results to `outputs/`

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

### 1. Data Preprocessing
- Load Excel data
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
- Generate 36-60 month forecast
- Calculate 95% confidence intervals
- Comprehensive visualization

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

### Changing Forecast Horizon

In `notebooks/02_arima_modeling.ipynb` or `src/arima_forecast.py`:
```python
forecast_steps = 60  # Change to desired number of months
```

### Adjusting Train-Test Split

```python
train_size = int(len(df_ts) * 0.8)  # Change 0.8 to desired ratio
```

### Enabling Seasonal ARIMA

In `auto_arima()`:
```python
auto_model = auto_arima(
    train,
    seasonal=True,      # Enable seasonality
    m=12,               # Seasonal period (12 for monthly data)
    ...
)
```

## 📚 Dependencies

Key packages:
- `pandas`: Data manipulation
- `numpy`: Numerical operations
- `matplotlib`, `seaborn`: Visualization
- `statsmodels`: ARIMA modeling and statistical tests
- `pmdarima`: Auto ARIMA parameter selection
- `scipy`, `sklearn`: Statistical analysis and metrics
- `openpyxl`: Excel file handling

See `requirements.txt` for complete list with versions.

## 🐛 Troubleshooting

### Installation Issues
```bash
# If pmdarima installation fails, try:
pip install pmdarima --no-build-isolation

# For openpyxl issues:
pip install --upgrade openpyxl
```

### Jupyter Notebook Not Found
```bash
# Verify jupyter is installed:
pip install --upgrade jupyter notebook
```

### Data Loading Errors
- Ensure `ProductForecast.xlsx` is in the `data/` directory
- Check that file path is correct in scripts/notebooks

## 📞 Support

For issues or questions:
1. Check error messages in notebook/script output
2. Verify all dependencies are installed
3. Ensure data file is in correct location

## 📄 License

This project is created for product forecasting analysis.

## 🙏 Acknowledgments

- Built with statsmodels and pmdarima libraries
- ARIMA methodology based on time series forecasting best practices

---

**Last Updated**: December 7, 2025

**Status**: ✅ Production Ready
