"""Product Forecasting Script (Grouped by Product)
===================================================

Generate individual ARIMA forecasting models for each Product.
For each product, all CustomerID records are aggregated together to train 
a single model. This enables efficient batch processing with parallel execution.

Workflow:
    1. Group data by Product (not Product-CustomerID)
    2. For each Product, aggregate all CustomerIDs' quantities
    3. Train one ARIMA model per Product
    4. Save model, metadata, and visualization immediately after training
    5. Process all products in parallel batches for speed

Expected Data Columns:
    - Year: Year of the transaction
    - Product: Specific product identifier
    - CustomerID: Customer identifier
    - Quantity: Sales/demand quantity

Usage:
    # Basic usage (looks for data/RawData-Forecast-TBD2.xlsx)
    python -m src.models.product_customer_forecast
    
    # With custom data file
    python -m src.models.product_customer_forecast --data "data/ProductForecast.xlsx"
    
    # Specify forecast horizon
    python -m src.models.product_customer_forecast --forecast-years 5
    
    # Enable visualizations
    python -m src.models.product_customer_forecast --visualize
    
    # Disable parallel processing (sequential mode)
    python -m src.models.product_customer_forecast --no-parallel

Author: ARIMA Forecasting System
Date: 2025-12-30 (Updated: 2026-01-01)
"""

from __future__ import annotations

import argparse
import json
import logging
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "product_customer_forecasts"
MODELS_DIR = OUTPUT_DIR / "models"
METADATA_DIR = OUTPUT_DIR / "metadata"
VIZ_DIR = OUTPUT_DIR / "visualizations"
PREDICTIONS_DIR = OUTPUT_DIR / "model_predictions"


@dataclass
class ForecastConfig:
    """Configuration for forecasting parameters."""
    
    data_path: Optional[Path] = None
    dataframe: Optional[pd.DataFrame] = None  # Optional DataFrame to hold loaded data
        
        
    forecast_years: int = 3  # Default: 3 years of forecasting

    min_observations: int = 5  # Minimum 5 years for reliable ARIMA (was 3)
    visualize: bool = False
    train_test_split: float = 0.8
    seasonal_period: int = 1  # No seasonality for yearly data
    confidence_level: float = 0.95
    aggregation_mode: str = "yearly"  # "yearly" data aggregation (default)
    parallel_processing: bool = True  # Default: enabled for faster processing
    num_workers: int = 4
    round_forecasts: bool = True
    filter_product: Optional[str] = None
    filter_customer: Optional[str] = None
    # ARIMA search space configuration
    arima_max_p: int = 3  # Max AR order (was 2)
    arima_max_q: int = 3  # Max MA order (was 2)
    arima_max_order: Optional[int] = None  # Max p+q+d (None = no limit)
    validate_data: bool = True  # Enable data quality validation
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.forecast_years < 1:
            raise ValueError("forecast_years must be >= 1")
        if not 0 < self.train_test_split < 1:
            raise ValueError("train_test_split must be between 0 and 1")
        if self.min_observations < 5:
            logger.warning(
                f"min_observations={self.min_observations} is less than recommended minimum of 5. "
                "This may produce unreliable forecasts."
            )
        if self.num_workers < 1:
            raise ValueError("num_workers must be >= 1")
        if self.arima_max_p < 0 or self.arima_max_q < 0:
            raise ValueError("ARIMA max_p and max_q must be >= 0")
    
    @property
    def forecast_periods(self) -> int:
        """Get forecast periods (for backward compatibility and internal use)."""
        return self.forecast_years


@dataclass
class ModelResult:
    """Container for model results."""
    
    product: str
    customer_ids: List[str]  # List of all CustomerIDs for this product
    order: Optional[Tuple[int, int, int]] = None
    seasonal_order: Optional[Tuple[int, int, int, int]] = None
    rmse: Optional[float] = None
    mae: Optional[float] = None
    mape: Optional[float] = None
    forecast: Optional[pd.DataFrame] = None
    historical_data: Optional[pd.DataFrame] = None  # Store historical data for visualization
    error_message: Optional[str] = None
    success: bool = True
    num_customers: int = 0  # Number of customers for this product
    model_type: str = "ARIMA"  # Type of model used


class ProductCustomerForecaster:
    """Forecasting system grouped by Product.
    
    Groups data by Product, aggregates all CustomerID records for each product,
    trains one ARIMA model per product, and saves results immediately.
    Supports parallel batch processing for speed.
    """
    
    def __init__(self, config: ForecastConfig):
        self.config = config
        self.results: List[ModelResult] = []
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Create output directories if they don't exist."""
        for directory in [OUTPUT_DIR, MODELS_DIR, METADATA_DIR, VIZ_DIR, PREDICTIONS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directories ready: {OUTPUT_DIR}")
    
    def _validate_data_quality(self, df: pd.DataFrame) -> None:
        """Validate data quality and log warnings."""
        if not self.config.validate_data:
            return
        
        logger.info("Running data quality validation...")
        
        # Check for missing values
        missing_counts = df.isnull().sum()
        if missing_counts.any():
            logger.warning(f"Missing values detected:\n{missing_counts[missing_counts > 0]}")
        
        # Check for negative quantities
        if 'Quantity' in df.columns:
            negative_count = (df['Quantity'] < 0).sum()
            if negative_count > 0:
                logger.warning(f"Found {negative_count} negative quantity values")
            
            zero_count = (df['Quantity'] == 0).sum()
            if zero_count > 0:
                logger.info(f"Found {zero_count} zero quantity values ({zero_count/len(df)*100:.2f}%)")
        
        # Check for duplicates
        dup_count = df.duplicated().sum()
        if dup_count > 0:
            logger.warning(f"Found {dup_count} duplicate records")
        
        # Check for outliers
        if 'Quantity' in df.columns:
            Q1 = df['Quantity'].quantile(0.25)
            Q3 = df['Quantity'].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            outliers = df[(df['Quantity'] < lower_bound) | (df['Quantity'] > upper_bound)]
            if len(outliers) > 0:
                logger.info(
                    f"Detected {len(outliers)} outliers ({len(outliers)/len(df)*100:.2f}%) "
                    f"outside range [{lower_bound:.2f}, {upper_bound:.2f}]"
                )
        
        logger.info("Data quality validation complete")
    
    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Preprocess data: column mapping and validation."""
        logger.info(f"Preprocessing data: {len(df)} records")
        logger.info(f"Columns: {', '.join(df.columns.tolist())}")
        
        # Auto-map common column name variations
        column_mapping = {
            'Time': 'Year',
            'CUSTID': 'CustomerID',
            'ItemCode': 'Product',
            'Number': 'Quantity'
        }
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df = df.rename(columns={old_col: new_col})
                logger.info(f"Mapped column: {old_col} → {new_col}")
        
        # Validate data quality
        self._validate_data_quality(df)
        
        return df
    
    def load_data(self) -> pd.DataFrame:
        """Load and preprocess the data from file."""
        logger.info(f"Loading data from: {self.config.data_path}")
        
        if not self.config.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.config.data_path}")
        
        # Load Excel or CSV
        if self.config.data_path.suffix == ".csv":
            df = pd.read_csv(self.config.data_path)
        else:
            df = pd.read_excel(self.config.data_path)
        
        return self._preprocess_data(df)
    # 
    def prepare_timeseries_data(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """Group data by Product only and create time series.
        
        Returns:
            Dict with product as key, containing:
                - 'ts_data': Time series DataFrame
                - 'customer_ids': List of unique CustomerIDs for this product
        """
        logger.info("Preparing time series data...")
        logger.info(f"Aggregation mode: {self.config.aggregation_mode}")
        logger.info(f"Grouping by: Product (aggregating all CustomerIDs per product)")
        
        # Validate required columns
        required_cols = ['Year', 'Product', 'CustomerID', 'Quantity']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        grouped_data = {}
        
        if self.config.aggregation_mode == 'yearly':
            # Yearly aggregation (default mode) - Group by Product only
            for product, group in df.groupby('Product'):
                # Get all unique CustomerIDs for this product
                customer_ids = group['CustomerID'].unique().tolist()
                
                # Aggregate by year (sum across all customers)
                ts_data = group.groupby('Year')['Quantity'].sum().reset_index()
                
                # Check for gaps in years before creating time series
                years = sorted(ts_data['Year'].unique())
                if len(years) > 1:
                    year_gaps = np.diff(years)
                    if np.any(year_gaps > 1):
                        logger.warning(
                            f"Product {product}: Time series has gaps in years {years}. "
                            "Missing years will be filled with 0."
                        )
                
                ts_data['Date'] = pd.to_datetime(ts_data['Year'].astype(str) + '-01-01')
                ts_data = ts_data[['Date', 'Quantity']].set_index('Date')
                ts_data = ts_data.asfreq('YS', fill_value=0)  # Yearly start frequency
                
                # Filter by minimum observations
                if len(ts_data) >= self.config.min_observations:
                    grouped_data[product] = {
                        'ts_data': ts_data,
                        'customer_ids': customer_ids
                    }
        else:
            # Monthly aggregation (fallback for backward compatibility)
            if 'Month' not in df.columns:
                raise ValueError("Month column is required for monthly aggregation mode")
            
            # Clean data
            df = df.dropna(subset=['Year', 'Month'])
            df['Year'] = df['Year'].astype(int)
            df['Month'] = df['Month'].astype(int)
            df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-' + df['Month'].astype(str).str.zfill(2) + '-01')
            
            for product, group in df.groupby('Product'):
                # Get all unique CustomerIDs for this product
                customer_ids = group['CustomerID'].unique().tolist()
                
                # Aggregate by date (sum across all customers)
                ts_data = group.groupby('Date')['Quantity'].sum().reset_index()
                ts_data.set_index('Date', inplace=True)
                ts_data = ts_data.asfreq('MS', fill_value=0)  # Monthly start frequency
                
                # Only include if we have enough observations
                if len(ts_data) >= self.config.min_observations:
                    grouped_data[product] = {
                        'ts_data': ts_data,
                        'customer_ids': customer_ids
                    }
        
        # Print summary
        total_customers = sum(len(v['customer_ids']) for v in grouped_data.values())
        logger.info(f"Created {len(grouped_data)} Product groups")
        logger.info(f"Total unique CustomerIDs across products: {total_customers}")
        logger.info(f"Filtered out products with < {self.config.min_observations} observations")
        
        return grouped_data
    
    def train_arima_model(
        self, 
        product: str, 
        customer_ids: List[str], 
        ts_data: pd.DataFrame
    ) -> ModelResult:
        """Train ARIMA model for a single Product (aggregated across all customers)."""
        try:
            # Train-test split
            train_size = int(len(ts_data) * self.config.train_test_split)
            train = ts_data['Quantity'][:train_size]
            test = ts_data['Quantity'][train_size:]
            
            # Find optimal parameters
            # Adjust seasonality based on aggregation mode
            is_yearly = self.config.aggregation_mode == 'yearly'
            seasonal_enabled = not is_yearly  # Disable seasonality for yearly data
            seasonal_m = 1 if is_yearly else self.config.seasonal_period
            
            auto_model = auto_arima(
                train,
                start_p=0,
                start_q=0,
                max_p=self.config.arima_max_p,  # Configurable (default: 3)
                max_q=self.config.arima_max_q,  # Configurable (default: 3)
                max_order=self.config.arima_max_order,  # Configurable (default: None)
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
                
                # Calculate MAPE properly (exclude zero values)
                non_zero_mask = test.values != 0
                if np.any(non_zero_mask):
                    test_nonzero = test.values[non_zero_mask]
                    pred_nonzero = predictions.values[non_zero_mask]
                    mape = float(np.mean(np.abs((test_nonzero - pred_nonzero) / test_nonzero)) * 100)
                else:
                    mape = None  # Cannot calculate MAPE when all test values are zero
                    logger.warning(f"Product {product}: Cannot calculate MAPE (all test values are zero)")
                
                metrics = {'rmse': rmse, 'mae': mae, 'mape': mape}
            
            # Generate forecast
            forecast_result = fitted_model.get_forecast(steps=self.config.forecast_periods)
            forecast_values = forecast_result.predicted_mean
            
            # Determine frequency based on aggregation mode
            if self.config.aggregation_mode == 'yearly':
                freq = 'YS'
                offset = pd.DateOffset(years=1)
            else:
                freq = 'MS'
                offset = pd.DateOffset(months=1)
            
            forecast_dates = pd.date_range(
                start=ts_data.index[-1] + offset,
                periods=self.config.forecast_periods,
                freq=freq
            )
            
            forecast_df = pd.DataFrame({
                'Date': forecast_dates,
                'Forecast': forecast_values.values,
            })
            forecast_df.set_index('Date', inplace=True)
            
            # Post-process: Round to non-negative integers if enabled
            if self.config.round_forecasts:
                forecast_df['Forecast'] = forecast_df['Forecast'].clip(lower=0).round(0).astype(int)
            
            # Save model (named by product only)
            model_filename = f"{product}.pkl"
            model_path = MODELS_DIR / model_filename
            with open(model_path, 'wb') as f:
                pickle.dump(fitted_model, f)
            
            return ModelResult(
                product=product,
                customer_ids=customer_ids,
                order=best_order,
                seasonal_order=seasonal_order,
                rmse=metrics.get('rmse'),
                mae=metrics.get('mae'),
                mape=metrics.get('mape'),
                forecast=forecast_df,
                historical_data=ts_data,
                success=True,
                num_customers=len(customer_ids)
            )
            
        except Exception as e:
            return ModelResult(
                product=product,
                customer_ids=customer_ids,
                error_message=str(e),
                success=False,
                num_customers=len(customer_ids)
            )
    
    def create_visualization(
        self,
        product: str,
        customer_ids: List[str],
        historical: pd.DataFrame,
        forecast: pd.DataFrame
    ) -> None:
        """Create forecast visualization for a Product (aggregated across customers)."""
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
            
            # Vertical line at forecast start
            plt.axvline(
                x=historical.index[-1],
                color='green',
                linestyle=':',
                linewidth=2,
                label='Forecast Start'
            )
            
            plt.title(
                f'Forecast: {product} (Aggregated from {len(customer_ids)} Customers)',
                fontsize=14,
                fontweight='bold'
            )
            plt.xlabel('Date', fontsize=12)
            plt.ylabel('Quantity', fontsize=12)
            plt.legend(loc='best')
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save with error handling (named by product only)
            viz_path = VIZ_DIR / f"{product}.png"
            plt.savefig(viz_path, dpi=300, bbox_inches='tight')
            plt.close()
        except Exception as e:
            logger.warning(f"Failed to save visualization for {product}: {e}")
            plt.close()  # Ensure figure is closed even on error
    
    def save_metadata(self, result: ModelResult) -> None:
        """Save model metadata to JSON file."""
        # Helper to convert numpy types to native Python types
        def convert_to_native(val):
            if hasattr(val, 'item'):  # numpy scalar
                return val.item()
            if isinstance(val, list):
                return [convert_to_native(v) for v in val]
            return val
        
        metadata = {
            'product': convert_to_native(result.product),
            'customer_ids': convert_to_native(result.customer_ids),
            'num_customers': result.num_customers,
            'order': result.order,
            'seasonal_order': result.seasonal_order,
            'rmse': result.rmse,
            'mae': result.mae,
            'mape': result.mape,
            'forecast_years': self.config.forecast_years,
            'aggregation_mode': self.config.aggregation_mode,
            'success': result.success,
            'error_message': result.error_message,
            'generated_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Save metadata (named by product only)
        metadata_path = METADATA_DIR / f"{convert_to_native(result.product)}.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def get_results_dataframe(self) -> pd.DataFrame:
        """Get all forecast results as a consolidated DataFrame."""
        all_forecasts = []
        
        for result in self.results:
            if result.success and result.forecast is not None:
                # Add forecast data
                forecast_copy = result.forecast.reset_index()
                forecast_copy.insert(0, 'Product', result.product)
                forecast_copy.insert(1, 'Num_Customers', result.num_customers)
                all_forecasts.append(forecast_copy)
        
        if all_forecasts:
            return pd.concat(all_forecasts, ignore_index=True)
        else:
            return pd.DataFrame()
    
    def _train_single_product(self, args: Tuple) -> ModelResult:
        """Helper function for parallel processing of a single product."""
        product, data_dict = args
        ts_data = data_dict['ts_data']
        customer_ids = data_dict['customer_ids']
        
        # Train ARIMA model
        result = self.train_arima_model(product, customer_ids, ts_data)
        
        # Save metadata immediately after training
        self.save_metadata(result)
        
        # Create visualization if requested
        if self.config.visualize and result.success and result.forecast is not None:
            self.create_visualization(product, customer_ids, ts_data, result.forecast)
        
        return result
    
    def _run_parallel(self, grouped_data: Dict[str, Dict]) -> None:
        """Run model training in parallel using multiprocessing."""
        # Prepare arguments for parallel processing
        args_list = [
            (product, data_dict)
            for product, data_dict in grouped_data.items()
        ]
        
        # Run parallel processing with progress bar
        with mp.Pool(processes=self.config.num_workers) as pool:
            results = list(tqdm(
                pool.imap(self._train_single_product, args_list),
                total=len(args_list),
                desc="Training models (parallel)"
            ))
        
        self.results.extend(results)
    
    def run(self) -> None:
        """Main execution workflow."""
        logger.info("=" * 80)
        logger.info("PRODUCT FORECASTING SYSTEM (Grouped by Product)")
        logger.info("=" * 80)
        
        # Load data from file or use provided dataframe (only one source is used)
        if self.config.data_path is not None:
            logger.info(f"Loading data from file: {self.config.data_path}")
            df = self.load_data()
        elif self.config.dataframe is not None:
            logger.info("Using provided dataframe (e.g., from ImportFromErp)")
            df = self._preprocess_data(self.config.dataframe.copy())
        else:
            raise ValueError("Either data_path or dataframe must be provided")
        
        # Apply filters if specified
        if self.config.filter_product:
            logger.info(f"Filtering by Product: {self.config.filter_product}")
            df = df[df['Product'] == self.config.filter_product]
            
        if self.config.filter_customer:
            logger.info(f"Filtering by CustomerID: {self.config.filter_customer}")
            # Ensure string comparison for CustomerID
            df = df[df['CustomerID'].astype(str) == str(self.config.filter_customer)]
            
        if len(df) == 0:
            logger.error("No data found after applying filters!")
            return

        # Prepare time series data
        grouped_data = self.prepare_timeseries_data(df)
        
        if len(grouped_data) == 0:
            logger.error("No valid Product groups found!")
            logger.error(f"Ensure products have at least {self.config.min_observations} observations")
            return
        
        # Train models
        logger.info("Training ARIMA models...")
        logger.info(f"Processing {len(grouped_data)} products...")
        logger.info(f"Aggregation mode: {self.config.aggregation_mode}")
        logger.info(f"Parallel processing: {'Enabled' if self.config.parallel_processing else 'Disabled'}")
        
        if self.config.parallel_processing:
            # Parallel processing
            logger.info(f"Using {self.config.num_workers} workers")
            self._run_parallel(grouped_data)
        else:
            # Sequential processing
            for product, data_dict in tqdm(grouped_data.items(), desc="Training models"):
                ts_data = data_dict['ts_data']
                customer_ids = data_dict['customer_ids']
                
                # Train ARIMA model
                result = self.train_arima_model(product, customer_ids, ts_data)
                
                self.results.append(result)
                
                # Save metadata immediately after training
                self.save_metadata(result)
                
                # Create visualization if requested and successful
                if self.config.visualize and result.success and result.forecast is not None:
                    self.create_visualization(product, customer_ids, ts_data, result.forecast)
        
        # Print summary
        successful = sum(1 for r in self.results if r.success)
        failed = len(self.results) - successful
        total_customers = sum(r.num_customers for r in self.results if r.success)
        
        logger.info("=" * 80)
        logger.info("FORECAST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Products: {len(self.results)}")
        logger.info(f"Total Customers (aggregated): {total_customers}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        
        if successful > 0:
            # Filter out None values before calculating average
            valid_mapes = [r.mape for r in self.results if r.success and r.mape is not None]
            if valid_mapes:
                avg_mape = np.mean(valid_mapes)
                logger.info(f"Average MAPE: {avg_mape:.2f}%")
            else:
                logger.info("Average MAPE: N/A (insufficient test data)")
        
        logger.info(f"Forecast Horizon: {self.config.forecast_years} years")
        logger.info(f"Results saved to: {OUTPUT_DIR}")
        logger.info("=" * 80)
        logger.info("ANALYSIS COMPLETE!")
        logger.info("Tip: Call forecaster.export_results() to generate Excel/CSV exports")

    def export_results(self) -> None:
        """Export all results to Excel and CSV files (for local use).
        
        This method exports forecast results to local Excel and CSV files.
        Use this when you need to review results locally or share them as files.
        
        Note: This is different from ExportToErp() which will be implemented
        separately for ERP system integration.
        
        Usage:
            forecaster.export_results()
        
        Output files:
            - outputs/product_customer_forecasts/consolidated_forecasts.xlsx
            - outputs/product_customer_forecasts/forecast_summary.csv
        """
        print("\nExporting results...")
        
        # Prepare summary data
        summary_rows = []
        all_forecasts = []
        
        for result in self.results:
            summary_row = {
                'Product': result.product,
                'Num_Customers': result.num_customers,
                'CustomerIDs': ', '.join(str(c) for c in result.customer_ids[:10]) + ('...' if len(result.customer_ids) > 10 else ''),
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
                forecast_copy.insert(1, 'Num_Customers', result.num_customers)
                forecast_copy.insert(2, 'CustomerID', ', '.join(str(c) for c in result.customer_ids[:5]) + ('...' if len(result.customer_ids) > 5 else ''))
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


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Product-Customer Forecasting System - Yearly Aggregation Mode'
    )
    parser.add_argument(
        '--data',
        type=str,
        default='data/RawData-Forecast-TBD2.xlsx',
        help='Path to data file (Excel or CSV)'
    )
    parser.add_argument(
        '--forecast-years',
        type=int,
        default=3,
        help='Number of years to forecast (default: 3)'
    )
    parser.add_argument(
        '--min-observations',
        type=int,
        default=5,
        help='Minimum observations (years) required per combination (default: 5)'
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
        default='yearly',
        help='Time aggregation mode: yearly (default) or monthly'
    )
    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='Disable parallel processing (parallel is enabled by default)'
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
    parser.add_argument(
        '--product',
        type=str,
        help='Filter by specific Product'
    )
    parser.add_argument(
        '--customer',
        type=str,
        help='Filter by specific CustomerID'
    )
    
    args = parser.parse_args()
    
    # Resolve data path
    data_path = Path(args.data)
    if not data_path.is_absolute():
        data_path = PROJECT_ROOT / data_path
    
    # Create configuration
    config = ForecastConfig(
        data_path=data_path,
        forecast_years=args.forecast_years,
        min_observations=args.min_observations,
        visualize=args.visualize,
        aggregation_mode=args.aggregation,
        parallel_processing=not args.no_parallel,  # Default True, disable with --no-parallel
        num_workers=args.workers,
        round_forecasts=args.round_forecasts,
        filter_product=args.product,
        filter_customer=args.customer
    )
    
    # Run forecasting
    forecaster = ProductCustomerForecaster(config)
    forecaster.run()


if __name__ == '__main__':
    main()
