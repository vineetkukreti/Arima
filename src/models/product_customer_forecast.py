"""Product-Customer Forecasting Script
=======================================

Generate individual ARIMA or Prophet forecasting models for each Product-CustomerID
combination. This enables granular analysis of product performance per customer.

Expected Data Columns:
    - Year: Year of the transaction
    - Month: Month of the transaction
    - Product Category: Category classification
    - Product: Specific product identifier
    - CustomerID: Customer identifier
    - Quantity: Sales/demand quantity

Usage:
    # Basic usage (looks for data/RawData-Forecast-TBD2.xlsx)
    python -m src.models.product_customer_forecast
    
    # With custom data file
    python -m src.models.product_customer_forecast --data "data/ProductForecast.xlsx"
    
    # Specify forecast horizon
    python -m src.models.product_customer_forecast --forecast-months 24
    
    # Use Prophet instead of ARIMA
    python -m src.models.product_customer_forecast --model-type prophet
    
    # Enable visualizations
    python -m src.models.product_customer_forecast --visualize

Author: ARIMA Forecasting System
Date: 2025-12-16
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import pickle
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pmdarima import auto_arima
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.arima.model import ARIMA
from tqdm import tqdm

warnings.filterwarnings("ignore")

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "product_customer_forecasts"
MODELS_DIR = OUTPUT_DIR / "models"
METADATA_DIR = OUTPUT_DIR / "metadata"
VIZ_DIR = OUTPUT_DIR / "visualizations"


@dataclass
class ForecastConfig:
    """Configuration for forecasting parameters."""
    
    data_path: Path
    forecast_months: int = 12
    min_observations: int = 24
    model_type: str = "arima"  # "arima" or "prophet"
    visualize: bool = False
    train_test_split: float = 0.8
    seasonal_period: int = 12
    confidence_level: float = 0.95
    aggregation_mode: str = "monthly"  # "monthly" or "yearly"
    parallel_processing: bool = False
    num_workers: int = 4
    round_forecasts: bool = True


@dataclass
class ModelResult:
    """Container for model results."""
    
    product: str
    customer_id: str
    product_category: str
    model_type: str
    order: Optional[Tuple[int, int, int]] = None
    seasonal_order: Optional[Tuple[int, int, int, int]] = None
    rmse: Optional[float] = None
    mae: Optional[float] = None
    mape: Optional[float] = None
    forecast: Optional[pd.DataFrame] = None
    error_message: Optional[str] = None
    success: bool = True


class ProductCustomerForecaster:
    """Forecasting system for Product-CustomerID combinations."""
    
    def __init__(self, config: ForecastConfig):
        self.config = config
        self.results: List[ModelResult] = []
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Create output directories if they don't exist."""
        for directory in [OUTPUT_DIR, MODELS_DIR, METADATA_DIR, VIZ_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ Output directories ready: {OUTPUT_DIR}")
    
    def load_data(self) -> pd.DataFrame:
        """Load and preprocess the data."""
        print(f"\nLoading data from: {self.config.data_path}")
        
        if not self.config.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.config.data_path}")
        
        # Load Excel or CSV
        if self.config.data_path.suffix == ".csv":
            df = pd.read_csv(self.config.data_path)
        else:
            df = pd.read_excel(self.config.data_path)
        
        print(f"✓ Loaded {len(df)} records")
        print(f"  Columns: {', '.join(df.columns.tolist())}")
        
        return df
    
    def prepare_timeseries_data(self, df: pd.DataFrame) -> Dict[Tuple[str, str, str], pd.DataFrame]:
        """Group data by Product-CustomerID-Category and create time series."""
        print("\nPreparing time series data...")
        print(f"  Aggregation mode: {self.config.aggregation_mode}")
        
        # Validate required columns
        required_cols = ['Year', 'Month', 'Product', 'CustomerID', 'Product Category', 'Quantity']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        if self.config.aggregation_mode == 'yearly':
            # Yearly aggregation
            grouped_data = {}
            
            for (product, customer_id, category), group in df.groupby(['Product', 'CustomerID', 'Product Category']):
                # Aggregate by year
                ts_data = group.groupby('Year')['Quantity'].sum().reset_index()
                ts_data['Date'] = pd.to_datetime(ts_data['Year'].astype(str) + '-01-01')
                ts_data = ts_data[['Date', 'Quantity']].set_index('Date')
                ts_data = ts_data.asfreq('YS', fill_value=0)  # Yearly start frequency
                
                # Adjust minimum observations for yearly data (e.g., 3 years minimum)
                min_obs_yearly = max(3, self.config.min_observations // 12)
                if len(ts_data) >= min_obs_yearly:
                    grouped_data[(product, customer_id, category)] = ts_data
        else:
            # Monthly aggregation (default)
            df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-' + df['Month'].astype(str).str.zfill(2) + '-01')
            grouped_data = {}
            
            for (product, customer_id, category), group in df.groupby(['Product', 'CustomerID', 'Product Category']):
                # Aggregate by date and sum quantities
                ts_data = group.groupby('Date')['Quantity'].sum().reset_index()
                ts_data.set_index('Date', inplace=True)
                ts_data = ts_data.asfreq('MS', fill_value=0)  # Monthly start frequency
                
                # Only include if we have enough observations
                if len(ts_data) >= self.config.min_observations:
                    grouped_data[(product, customer_id, category)] = ts_data
        
        print(f"✓ Created {len(grouped_data)} Product-CustomerID-Category combinations")
        min_obs = max(3, self.config.min_observations // 12) if self.config.aggregation_mode == 'yearly' else self.config.min_observations
        print(f"  (Filtered out combinations with < {min_obs} observations)")
        
        return grouped_data
    
    def train_arima_model(
        self, 
        product: str, 
        customer_id: str, 
        product_category: str,
        ts_data: pd.DataFrame
    ) -> ModelResult:
        """Train ARIMA model for a single Product-CustomerID-Category combination."""
        try:
            # Train-test split
            train_size = int(len(ts_data) * self.config.train_test_split)
            train = ts_data['Quantity'][:train_size]
            test = ts_data['Quantity'][train_size:]
            
            # Find optimal parameters (optimized for speed)
            # Adjust seasonality based on aggregation mode
            is_yearly = self.config.aggregation_mode == 'yearly'
            seasonal_enabled = not is_yearly  # Disable seasonality for yearly data
            seasonal_m = 1 if is_yearly else self.config.seasonal_period
            
            auto_model = auto_arima(
                train,
                start_p=0,
                start_q=0,
                max_p=2,  # Reduced from 3 for speed
                max_q=2,  # Reduced from 3 for speed
                max_order=5,  # Limit total complexity
                d=None,
                D=1 if seasonal_enabled else 0,
                seasonal=seasonal_enabled,
                m=seasonal_m,
                stepwise=True,
                suppress_warnings=True,
                error_action="ignore",
                trace=False,
            )
            
            best_order = auto_model.order
            seasonal_order = auto_model.seasonal_order
            
            # Train on full data
            model = ARIMA(
                ts_data['Quantity'],
                order=best_order,
                seasonal_order=seasonal_order
            )
            fitted_model = model.fit()
            
            # Evaluate on test set (if available)
            metrics = {}
            if len(test) > 0:
                predictions = fitted_model.forecast(steps=len(test))
                mse = mean_squared_error(test, predictions)
                rmse = float(np.sqrt(mse))
                mae = mean_absolute_error(test, predictions)
                # Avoid division by zero in MAPE
                mape = float(np.mean(np.abs((test - predictions) / (test + 1e-10))) * 100)
                
                metrics = {'rmse': rmse, 'mae': mae, 'mape': mape}
            
            # Generate forecast
            forecast_result = fitted_model.get_forecast(steps=self.config.forecast_months)
            forecast_values = forecast_result.predicted_mean
            forecast_ci = forecast_result.conf_int(alpha=1 - self.config.confidence_level)
            
            # Determine frequency based on aggregation mode
            if self.config.aggregation_mode == 'yearly':
                freq = 'YS'
                offset = pd.DateOffset(years=1)
            else:
                freq = 'MS'
                offset = pd.DateOffset(months=1)
            
            forecast_dates = pd.date_range(
                start=ts_data.index[-1] + offset,
                periods=self.config.forecast_months,
                freq=freq
            )
            
            forecast_df = pd.DataFrame({
                'Date': forecast_dates,
                'Forecast': forecast_values.values,
                'Lower_CI': forecast_ci.iloc[:, 0].values,
                'Upper_CI': forecast_ci.iloc[:, 1].values,
            })
            forecast_df.set_index('Date', inplace=True)
            
            # Post-process: Round to non-negative integers if enabled
            if self.config.round_forecasts:
                forecast_df['Forecast'] = forecast_df['Forecast'].clip(lower=0).round(0).astype(int)
                forecast_df['Lower_CI'] = forecast_df['Lower_CI'].clip(lower=0).round(0).astype(int)
                forecast_df['Upper_CI'] = forecast_df['Upper_CI'].clip(lower=0).round(0).astype(int)
            
            # Save model
            model_filename = f"{product}_{customer_id}_{product_category}.pkl"
            model_path = MODELS_DIR / model_filename
            with open(model_path, 'wb') as f:
                pickle.dump(fitted_model, f)
            
            return ModelResult(
                product=product,
                customer_id=customer_id,
                product_category=product_category,
                model_type='ARIMA',
                order=best_order,
                seasonal_order=seasonal_order,
                rmse=metrics.get('rmse'),
                mae=metrics.get('mae'),
                mape=metrics.get('mape'),
                forecast=forecast_df,
                success=True
            )
            
        except Exception as e:
            return ModelResult(
                product=product,
                customer_id=customer_id,
                product_category=product_category,
                model_type='ARIMA',
                error_message=str(e),
                success=False
            )
    
    def train_prophet_model(
        self,
        product: str,
        customer_id: str,
        product_category: str,
        ts_data: pd.DataFrame
    ) -> ModelResult:
        """Train Prophet model for a single Product-CustomerID-Category combination."""
        try:
            from prophet import Prophet
            
            # Prepare data for Prophet
            prophet_df = ts_data.reset_index()
            prophet_df.columns = ['ds', 'y']
            
            # Train-test split
            train_size = int(len(prophet_df) * self.config.train_test_split)
            train = prophet_df[:train_size]
            test = prophet_df[train_size:]
            
            # Initialize and fit Prophet model
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                interval_width=self.config.confidence_level
            )
            model.fit(train)
            
            # Evaluate on test set (if available)
            metrics = {}
            if len(test) > 0:
                forecast_test = model.predict(test[['ds']])
                predictions = forecast_test['yhat'].values
                actuals = test['y'].values
                
                mse = mean_squared_error(actuals, predictions)
                rmse = float(np.sqrt(mse))
                mae = mean_absolute_error(actuals, predictions)
                mape = float(np.mean(np.abs((actuals - predictions) / (actuals + 1e-10))) * 100)
                
                metrics = {'rmse': rmse, 'mae': mae, 'mape': mape}
            
            # Retrain on full data
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                interval_width=self.config.confidence_level
            )
            model.fit(prophet_df)
            
            # Generate forecast
            freq_str = 'YS' if self.config.aggregation_mode == 'yearly' else 'MS'
            future = model.make_future_dataframe(periods=self.config.forecast_months, freq=freq_str)
            forecast = model.predict(future)
            
            # Extract future forecast only
            forecast_df = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].iloc[-self.config.forecast_months:]
            forecast_df.columns = ['Date', 'Forecast', 'Lower_CI', 'Upper_CI']
            forecast_df.set_index('Date', inplace=True)
            
            # Post-process: Round to non-negative integers if enabled
            if self.config.round_forecasts:
                forecast_df['Forecast'] = forecast_df['Forecast'].clip(lower=0).round(0).astype(int)
                forecast_df['Lower_CI'] = forecast_df['Lower_CI'].clip(lower=0).round(0).astype(int)
                forecast_df['Upper_CI'] = forecast_df['Upper_CI'].clip(lower=0).round(0).astype(int)
            
            # Save model
            model_filename = f"{product}_{customer_id}_{product_category}.pkl"
            model_path = MODELS_DIR / model_filename
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            
            return ModelResult(
                product=product,
                customer_id=customer_id,
                product_category=product_category,
                model_type='Prophet',
                rmse=metrics.get('rmse'),
                mae=metrics.get('mae'),
                mape=metrics.get('mape'),
                forecast=forecast_df,
                success=True
            )
            
        except ImportError:
            return ModelResult(
                product=product,
                customer_id=customer_id,
                product_category=product_category,
                model_type='Prophet',
                error_message="Prophet not installed. Run: pip install prophet",
                success=False
            )
        except Exception as e:
            return ModelResult(
                product=product,
                customer_id=customer_id,
                product_category=product_category,
                model_type='Prophet',
                error_message=str(e),
                success=False
            )
    
    def create_visualization(
        self,
        product: str,
        customer_id: str,
        product_category: str,
        historical: pd.DataFrame,
        forecast: pd.DataFrame
    ) -> None:
        """Create forecast visualization for a Product-CustomerID-Category combination."""
        try:
            plt.figure(figsize=(14, 6))
            
            # Plot historical data
            plt.plot(
                historical.index,
                historical['Quantity'],
                label='Historical',
                linewidth=2,
                color='blue'
            )
            
            # Plot forecast
            plt.plot(
                forecast.index,
                forecast['Forecast'],
                label='Forecast',
                linewidth=2,
                color='red',
                linestyle='--'
            )
            
            # Confidence interval
            plt.fill_between(
                forecast.index,
                forecast['Lower_CI'],
                forecast['Upper_CI'],
                alpha=0.3,
                color='red',
                label=f'{int(self.config.confidence_level * 100)}% Confidence Interval'
            )
            
            # Vertical line at forecast start
            plt.axvline(
                x=historical.index[-1],
                color='green',
                linestyle=':',
                linewidth=2,
                label='Forecast Start'
            )
            
            plt.title(
                f'Forecast: {product} ({product_category}) - Customer {customer_id}',
                fontsize=14,
                fontweight='bold'
            )
            plt.xlabel('Date', fontsize=12)
            plt.ylabel('Quantity', fontsize=12)
            plt.legend(loc='best')
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save with error handling
            viz_path = VIZ_DIR / f"{product}_{customer_id}_{product_category}.png"
            plt.savefig(viz_path, dpi=300, bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"  Warning: Failed to save visualization for {product}_{customer_id}_{product_category}: {e}")
            plt.close()  # Ensure figure is closed even on error
    
    def save_metadata(self, result: ModelResult) -> None:
        """Save model metadata to JSON file."""
        metadata = {
            'product': result.product,
            'customer_id': result.customer_id,
            'product_category': result.product_category,
            'model_type': result.model_type,
            'order': result.order,
            'seasonal_order': result.seasonal_order,
            'rmse': result.rmse,
            'mae': result.mae,
            'mape': result.mape,
            'forecast_months': self.config.forecast_months,
            'aggregation_mode': self.config.aggregation_mode,
            'success': result.success,
            'error_message': result.error_message,
            'generated_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        metadata_path = METADATA_DIR / f"{result.product}_{result.customer_id}_{result.product_category}.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def export_results(self, grouped_data: Dict[Tuple[str, str, str], pd.DataFrame]) -> None:
        """Export all results to Excel and CSV."""
        print("\nExporting results...")
        
        # Prepare summary data
        summary_rows = []
        all_forecasts = []
        
        for result in self.results:
            summary_row = {
                'Product': result.product,
                'CustomerID': result.customer_id,
                'Product_Category': result.product_category,
                'Model_Type': result.model_type,
                'ARIMA_Order': str(result.order) if result.order else 'N/A',
                'Seasonal_Order': str(result.seasonal_order) if result.seasonal_order else 'N/A',
                'RMSE': f"{result.rmse:.2f}" if result.rmse else 'N/A',
                'MAE': f"{result.mae:.2f}" if result.mae else 'N/A',
                'MAPE': f"{result.mape:.2f}%" if result.mape else 'N/A',
                'Success': result.success,
                'Error': result.error_message if result.error_message else ''
            }
            summary_rows.append(summary_row)
            
            if result.success and result.forecast is not None:
                # Add forecast data
                forecast_copy = result.forecast.reset_index()
                forecast_copy.insert(0, 'Product', result.product)
                forecast_copy.insert(1, 'CustomerID', result.customer_id)
                forecast_copy.insert(2, 'Product_Category', result.product_category)
                all_forecasts.append(forecast_copy)
        
        summary_df = pd.DataFrame(summary_rows)
        
        # Export to Excel
        excel_path = OUTPUT_DIR / 'consolidated_forecasts.xlsx'
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            if all_forecasts:
                forecasts_df = pd.concat(all_forecasts, ignore_index=True)
                forecasts_df.to_excel(writer, sheet_name='All_Forecasts', index=False)
        
        print(f"✓ Excel report saved to: {excel_path}")
        
        # Export summary to CSV
        csv_path = OUTPUT_DIR / 'forecast_summary.csv'
        summary_df.to_csv(csv_path, index=False)
        print(f"✓ Summary CSV saved to: {csv_path}")
    
    def _train_single_combination(self, args: Tuple) -> ModelResult:
        """Helper function for parallel processing of a single combination."""
        product, customer_id, category, ts_data = args
        
        # Train model
        if self.config.model_type.lower() == 'prophet':
            result = self.train_prophet_model(product, customer_id, category, ts_data)
        else:
            result = self.train_arima_model(product, customer_id, category, ts_data)
        
        # Save metadata
        self.save_metadata(result)
        
        # Create visualization if requested
        if self.config.visualize and result.success and result.forecast is not None:
            self.create_visualization(product, customer_id, category, ts_data, result.forecast)
        
        return result
    
    def _run_parallel(self, grouped_data: Dict[Tuple[str, str, str], pd.DataFrame]) -> None:
        """Run model training in parallel using multiprocessing."""
        # Prepare arguments for parallel processing
        args_list = [
            (product, customer_id, category, ts_data)
            for (product, customer_id, category), ts_data in grouped_data.items()
        ]
        
        # Run parallel processing with progress bar
        with mp.Pool(processes=self.config.num_workers) as pool:
            results = list(tqdm(
                pool.imap(self._train_single_combination, args_list),
                total=len(args_list),
                desc="Training models (parallel)"
            ))
        
        self.results.extend(results)
    
    def run(self) -> None:
        """Main execution workflow."""
        print("=" * 80)
        print("PRODUCT-CUSTOMER FORECASTING SYSTEM")
        print("=" * 80)
        
        # Load data
        df = self.load_data()
        
        # Prepare time series data
        grouped_data = self.prepare_timeseries_data(df)
        
        if len(grouped_data) == 0:
            print("\n✗ No valid Product-CustomerID-Category combinations found!")
            print(f"  Ensure combinations have at least {self.config.min_observations} observations")
            return
        
        # Train models
        print(f"\nTraining {self.config.model_type.upper()} models...")
        print(f"Processing {len(grouped_data)} combinations...")
        print(f"Aggregation mode: {self.config.aggregation_mode}")
        print(f"Parallel processing: {'Enabled' if self.config.parallel_processing else 'Disabled'}\n")
        
        if self.config.parallel_processing:
            # Parallel processing
            print(f"Using {self.config.num_workers} workers\n")
            self._run_parallel(grouped_data)
        else:
            # Sequential processing
            for (product, customer_id, category), ts_data in tqdm(grouped_data.items(), desc="Training models"):
                # Train model
                if self.config.model_type.lower() == 'prophet':
                    result = self.train_prophet_model(product, customer_id, category, ts_data)
                else:
                    result = self.train_arima_model(product, customer_id, category, ts_data)
                
                self.results.append(result)
                
                # Save metadata
                self.save_metadata(result)
                
                # Create visualization if requested and successful
                if self.config.visualize and result.success and result.forecast is not None:
                    self.create_visualization(product, customer_id, category, ts_data, result.forecast)
        
        # Export results
        self.export_results(grouped_data)
        
        # Print summary
        successful = sum(1 for r in self.results if r.success)
        failed = len(self.results) - successful
        
        print("\n" + "=" * 80)
        print("FORECAST SUMMARY")
        print("=" * 80)
        print(f"Total Combinations: {len(self.results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        
        if successful > 0:
            avg_mape = np.mean([r.mape for r in self.results if r.success and r.mape])
            print(f"Average MAPE: {avg_mape:.2f}%")
        
        print(f"\nForecast Horizon: {self.config.forecast_months} months")
        print(f"Results saved to: {OUTPUT_DIR}")
        print("=" * 80)
        print("\n✓ ANALYSIS COMPLETE!")


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Product-Customer Forecasting System'
    )
    parser.add_argument(
        '--data',
        type=str,
        default='data/RawData-Forecast-TBD2.xlsx',
        help='Path to data file (Excel or CSV)'
    )
    parser.add_argument(
        '--forecast-months',
        type=int,
        default=12,
        help='Number of months to forecast (default: 12)'
    )
    parser.add_argument(
        '--min-observations',
        type=int,
        default=24,
        help='Minimum observations required per combination (default: 24)'
    )
    parser.add_argument(
        '--model-type',
        type=str,
        choices=['arima', 'prophet'],
        default='arima',
        help='Model type to use (default: arima)'
    )
    parser.add_argument(
        '--visualize',
        action='store_true',
        help='Generate visualizations for all combinations'
    )
    parser.add_argument(
        '--aggregation',
        type=str,
        choices=['monthly', 'yearly'],
        default='monthly',
        help='Time aggregation mode: monthly (default) or yearly for faster processing'
    )
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Enable parallel processing for faster execution'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=max(1, mp.cpu_count() - 1),
        help=f'Number of parallel workers (default: {max(1, mp.cpu_count() - 1)})'
    )
    parser.add_argument(
        '--round-forecasts',
        action='store_true',
        default=True,
        help='Round forecasts to non-negative integers (default: True)'
    )
    
    args = parser.parse_args()
    
    # Resolve data path
    data_path = Path(args.data)
    if not data_path.is_absolute():
        data_path = PROJECT_ROOT / data_path
    
    # Create configuration
    config = ForecastConfig(
        data_path=data_path,
        forecast_months=args.forecast_months,
        min_observations=args.min_observations,
        model_type=args.model_type,
        visualize=args.visualize,
        aggregation_mode=args.aggregation,
        parallel_processing=args.parallel,
        num_workers=args.workers,
        round_forecasts=args.round_forecasts
    )
    
    # Run forecasting
    forecaster = ProductCustomerForecaster(config)
    forecaster.run()


if __name__ == '__main__':
    main()
