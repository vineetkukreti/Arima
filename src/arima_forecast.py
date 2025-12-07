"""
ARIMA Product Forecasting Script
==================================

This script provides a production-ready implementation of ARIMA forecasting
for product demand/sales data.

Usage:
    python arima_forecast.py

The script will:
1. Load data from ../data/ProductForecast.xlsx
2. Aggregate by time period
3. Test for stationarity
4. Find optimal ARIMA parameters
5. Generate 60-month forecast
6. Export results to ../outputs/

Author: ARIMA Forecasting System
Date: 2025-12-07
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.arima.model import ARIMA
from pmdarima import auto_arima
from sklearn.metrics import mean_squared_error, mean_absolute_error
import warnings
import os
from datetime import datetime

warnings.filterwarnings('ignore')

# Configuration
# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, '../data/generated_data/synthetic_product_forecast.csv')
OUTPUT_DIR = os.path.join(BASE_DIR, '../outputs')
VIZ_DIR = os.path.join(BASE_DIR, '../outputs/visualizations')
FORECAST_STEPS = 60  # 60 months (5 years)


def ensure_directories():
    """Create output directories if they don't exist"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(VIZ_DIR, exist_ok=True)
    print(f"✓ Output directories ready: {OUTPUT_DIR}, {VIZ_DIR}")


def load_and_aggregate_data(file_path):
    """
    Load Excel data and aggregate by time period
    
    Args:
        file_path (str): Path to Excel file
        
    Returns:
        pd.DataFrame: Aggregated time series with Date index
    """
    print(f"\nLoading data from: {file_path}")
    if file_path.endswith('.csv'):
        df_raw = pd.read_csv(file_path)
    else:
        df_raw = pd.read_excel(file_path)
    print(f"✓ Loaded {df_raw.shape[0]} records")
    
    # Aggregate by Time period
    df_ts = df_raw.groupby('Time')['Number'].sum().reset_index()
    df_ts.columns = ['Date', 'Total_Number']
    
    # Convert to datetime and set as index
    df_ts['Date'] = pd.to_datetime(df_ts['Date'], format='%Y-%m')
    df_ts.set_index('Date', inplace=True)
    df_ts = df_ts.asfreq('MS')  # Monthly start frequency
    
    print(f"✓ Aggregated to {len(df_ts)} time periods")
    print(f"  Date range: {df_ts.index.min().strftime('%Y-%m')} to {df_ts.index.max().strftime('%Y-%m')}")
    
    return df_ts


def adf_test(timeseries, title=''):
    """
    Perform Augmented Dickey-Fuller test for stationarity
    
    Args:
        timeseries (pd.Series): Time series data
        title (str): Description for output
        
    Returns:
        bool: True if stationary, False otherwise
    """
    result = adfuller(timeseries.dropna(), autolag='AIC')
    
    print(f"\nADF Test - {title}:")
    print(f"  ADF Statistic: {result[0]:.4f}")
    print(f"  p-value: {result[1]:.4f}")
    
    if result[1] <= 0.05:
        print(f"  ✓ Series is STATIONARY (p-value <= 0.05)")
        return True
    else:
        print(f"  ✗ Series is NON-STATIONARY (p-value > 0.05)")
        return False


def find_optimal_arima(train_data):
    """
    Find optimal ARIMA parameters using auto_arima
    
    Args:
        train_data (pd.Series): Training time series
        
    Returns:
        tuple: Best ARIMA order (p, d, q)
    """
    print("\nFinding optimal ARIMA parameters...")
    
    auto_model = auto_arima(
        train_data,
        start_p=0, start_q=0,
        max_p=5, max_q=5,
        d=None,
        D=1,  # Force seasonal differencing
        seasonal=True,
        m=12,
        stepwise=True,
        suppress_warnings=True,
        error_action='ignore',
        trace=False
    )
    
    best_order = auto_model.order
    seasonal_order = auto_model.seasonal_order
    print(f"✓ Best ARIMA order found: {best_order}")
    print(f"  Seasonal Order: {seasonal_order}")
    print(f"  AIC: {auto_model.aic():.2f}")
    
    return best_order, seasonal_order


def train_and_evaluate(train, test, order, seasonal_order):
    """
    Train ARIMA model and evaluate on test set
    
    Args:
        train (pd.Series): Training data
        test (pd.Series): Test data
        order (tuple): ARIMA order (p, d, q)
        seasonal_order (tuple): Seasonal order (P, D, Q, m)
        
    Returns:
        dict: Performance metrics
    """
    print(f"\nTraining ARIMA{order}x{seasonal_order} model...")
    
    model = ARIMA(train, order=order, seasonal_order=seasonal_order)
    fitted_model = model.fit()
    
    # Make predictions
    predictions = fitted_model.forecast(steps=len(test))
    
    # Calculate metrics
    mse = mean_squared_error(test, predictions)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(test, predictions)
    mape = np.mean(np.abs((test - predictions) / test)) * 100
    
    metrics = {
        'MSE': mse,
        'RMSE': rmse,
        'MAE': mae,
        'MAPE': mape
    }
    
    print(f"✓ Model trained successfully")
    print(f"  RMSE: {rmse:.2f}")
    print(f"  MAPE: {mape:.2f}%")
    
    return metrics, fitted_model


def generate_forecast(full_data, order, seasonal_order, steps):
    """
    Generate future forecast using full dataset
    
    Args:
        full_data (pd.Series): Complete time series
        order (tuple): ARIMA order
        seasonal_order (tuple): Seasonal order
        steps (int): Number of periods to forecast
        
    Returns:
        pd.DataFrame: Forecast with confidence intervals
    """
    print(f"\nGenerating {steps}-month forecast...")
    
    # Fit model on full data
    model = ARIMA(full_data, order=order, seasonal_order=seasonal_order)
    fitted_model = model.fit()
    
    # Get forecast with confidence intervals
    forecast_result = fitted_model.get_forecast(steps=steps)
    forecast_values = forecast_result.predicted_mean
    forecast_ci = forecast_result.conf_int(alpha=0.05)
    
    # Create forecast dataframe
    forecast_dates = pd.date_range(
        start=full_data.index[-1] + pd.DateOffset(months=1),
        periods=steps,
        freq='MS'
    )
    
    forecast_df = pd.DataFrame({
        'Date': forecast_dates,
        'Forecast': forecast_values.values,
        'Lower_CI_95': forecast_ci.iloc[:, 0].values,
        'Upper_CI_95': forecast_ci.iloc[:, 1].values
    })
    forecast_df.set_index('Date', inplace=True)
    
    print(f"✓ Forecast generated")
    print(f"  Period: {forecast_df.index.min().strftime('%Y-%m')} to {forecast_df.index.max().strftime('%Y-%m')}")
    
    return forecast_df, fitted_model


def create_forecast_plot(historical, forecast, output_path):
    """
    Create and save forecast visualization
    
    Args:
        historical (pd.Series): Historical data
        forecast (pd.DataFrame): Forecast with CI
        output_path (str): Path to save plot
    """
    plt.figure(figsize=(16, 7))
    
    # Plot historical
    plt.plot(historical.index, historical, label='Historical Data', 
             linewidth=2.5, color='blue')
    
    # Plot forecast
    plt.plot(forecast.index, forecast['Forecast'], label='Forecast', 
             linewidth=2.5, color='red', linestyle='--')
    
    # Confidence interval
    plt.fill_between(forecast.index,
                     forecast['Lower_CI_95'],
                     forecast['Upper_CI_95'],
                     alpha=0.3, color='red', label='95% Confidence Interval')
    
    # Forecast start line
    plt.axvline(x=historical.index[-1], color='green', 
                linestyle=':', linewidth=2, label='Forecast Start')
    
    plt.title('ARIMA Product Forecast - 60 Month Projection', 
              fontsize=16, fontweight='bold')
    plt.xlabel('Date', fontsize=13)
    plt.ylabel('Total Number', fontsize=13)
    plt.legend(loc='best', fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Forecast plot saved to: {output_path}")


def export_results(historical, forecast, metrics, order, seasonal_order, output_dir):
    """
    Export results to Excel and CSV
    
    Args:
        historical (pd.DataFrame): Historical data
        forecast (pd.DataFrame): Forecast data
        metrics (dict): Performance metrics
        order (tuple): ARIMA order
        seasonal_order (tuple): Seasonal order
        output_dir (str): Output directory
    """
    # Prepare diagnostics
    diagnostics_data = {
        'Metric': ['ARIMA Order', 'Seasonal Order', 'RMSE (Test)', 'MAE (Test)', 'MAPE (Test)',
                   'Forecast Horizon', 'Generated On'],
        'Value': [str(order), str(seasonal_order), f"{metrics['RMSE']:.2f}", f"{metrics['MAE']:.2f}",
                  f"{metrics['MAPE']:.2f}%", f"{len(forecast)} months",
                  datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
    }
    diagnostics_df = pd.DataFrame(diagnostics_data)
    
    # Export to Excel
    excel_path = os.path.join(output_dir, 'forecast_results.xlsx')
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        historical.to_excel(writer, sheet_name='Historical_Data')
        forecast.to_excel(writer, sheet_name='Forecast')
        diagnostics_df.to_excel(writer, sheet_name='Model_Diagnostics', index=False)
    
    print(f"✓ Results exported to: {excel_path}")
    
    # Export forecast to CSV
    csv_path = os.path.join(output_dir, 'forecast_results.csv')
    forecast.to_csv(csv_path)
    print(f"✓ Forecast CSV saved to: {csv_path}")


def main():
    """Main execution function"""
    print("="*70)
    print("ARIMA PRODUCT FORECASTING SYSTEM")
    print("="*70)
    
    # Setup
    ensure_directories()
    
    # Load and prepare data
    df_ts = load_and_aggregate_data(DATA_PATH)
    
    # Test stationarity
    is_stationary = adf_test(df_ts['Total_Number'], title='Original Series')
    
    # Train-test split (80-20)
    train_size = int(len(df_ts) * 0.8)
    train = df_ts['Total_Number'][:train_size]
    test = df_ts['Total_Number'][train_size:]
    print(f"\nTrain-Test Split:")
    print(f"  Training: {len(train)} months")
    print(f"  Testing: {len(test)} months")
    
    # Find optimal parameters
    best_order, seasonal_order = find_optimal_arima(train)
    
    # Train and evaluate
    metrics, _ = train_and_evaluate(train, test, best_order, seasonal_order)
    
    # Generate final forecast
    forecast_df, final_model = generate_forecast(
        df_ts['Total_Number'], 
        best_order, 
        seasonal_order,
        FORECAST_STEPS
    )
    
    # Create visualization
    plot_path = os.path.join(VIZ_DIR, 'forecast_final.png')
    create_forecast_plot(df_ts['Total_Number'], forecast_df, plot_path)
    
    # Export results
    export_results(df_ts[['Total_Number']], forecast_df, metrics, best_order, seasonal_order, OUTPUT_DIR)
    
    # Summary
    print("\n" + "="*70)
    print("FORECAST SUMMARY")
    print("="*70)
    print(f"Model: ARIMA{best_order}x{seasonal_order}")
    print(f"Test MAPE: {metrics['MAPE']:.2f}%")
    print(f"Forecast Period: {forecast_df.index.min().strftime('%b %Y')} - {forecast_df.index.max().strftime('%b %Y')}")
    print(f"Average Forecast: {forecast_df['Forecast'].mean():.0f}")
    print(f"Forecast Range: {forecast_df['Forecast'].min():.0f} - {forecast_df['Forecast'].max():.0f}")
    print("="*70)
    print("\n✓ ANALYSIS COMPLETE!")
    print(f"\nResults saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
