"""ARIMA Forecasting Script
=========================

Generate ARIMA forecasts for Product-CustomerID combinations from Excel data.

This script uses the existing ProductCustomerForecaster infrastructure to
create demand forecasts using ARIMA models.

Usage:
    python run_optimizer.py
    
Expected Data:
    - Single Excel file OR a folder containing multiple Excel files
    - When using a folder, all Excel files will be automatically merged
    - All Excel files must have the same columns
    - Required columns: Year, Product, CustomerID, Product Category, Quantity
    - Default path: data/test_yearly_forecast.xlsx
    
Examples:
    - Single file: data/test_yearly_forecast.xlsx
    - Folder with multiple files: data/excel_files/
"""

import os
import sys
from pathlib import Path
import pandas as pd
from glob import glob

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.models.product_customer_forecast import (
        ProductCustomerForecaster,
        ForecastConfig
    )
except ImportError as e:
    print(f"Error: Could not import forecasting modules: {e}")
    print("Make sure src/models/product_customer_forecast.py exists")
    sys.exit(1)


def load_and_merge_excel_files(folder_path):
    """Load and merge all Excel files from a folder into a single dataframe.
    
    Args:
        folder_path: Path to folder containing Excel files
        
    Returns:
        Path to the merged temporary Excel file
    """
    folder = Path(folder_path)
    
    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    
    if not folder.is_dir():
        raise ValueError(f"Path is not a directory: {folder_path}")
    
    # Find all Excel files in the folder
    excel_files = list(folder.glob('*.xlsx')) + list(folder.glob('*.xls'))
    
    if not excel_files:
        raise ValueError(f"No Excel files found in folder: {folder_path}")
    
    print(f"\nFound {len(excel_files)} Excel file(s) in {folder_path}:")
    for file in excel_files:
        print(f"  - {file.name}")
    
    # Read and merge all Excel files
    print("\nReading and merging Excel files...")
    dataframes = []
    
    for file in excel_files:
        try:
            df = pd.read_excel(file)
            print(f"  ✓ Loaded {file.name}: {len(df)} rows, {len(df.columns)} columns")
            dataframes.append(df)
        except Exception as e:
            print(f"  ✗ Error reading {file.name}: {e}")
            continue
    
    if not dataframes:
        raise ValueError("Failed to read any Excel files")
    
    # Merge all dataframes
    merged_df = pd.concat(dataframes, ignore_index=True)
    print(f"\n✓ Merged data: {len(merged_df)} total rows, {len(merged_df.columns)} columns")
    
    # Save merged data to a temporary file
    temp_file = Path('data/temp_merged_data.csv')
    temp_file.parent.mkdir(parents=True, exist_ok=True)
    merged_df.to_csv(temp_file, index=False)
    print(f"✓ Saved merged data to: {temp_file}")
    
    return temp_file


def main():
    """Main execution function."""
    # Configuration - can be either a file or folder path
    data_path = Path('test_01')
    
    print("=" * 80)
    print("ARIMA FORECASTING SYSTEM")
    print("=" * 80)
    
    # Check if path is a directory (folder with multiple Excel files)
    if data_path.exists() and data_path.is_dir():
        print(f"\n📁 Folder mode: {data_path}")
        try:
            # Load and merge all Excel files from the folder
            data_path = load_and_merge_excel_files(data_path)
        except Exception as e:
            print(f"\n✗ Error merging Excel files: {e}")
            return
    
    # If not a directory, check if it's a file
    elif not data_path.exists():
        print(f"Path not found: {data_path}")
        print("\nTrying alternate sample data file...")
        data_path = Path('data/sample_product_customer_data.xlsx')
        
        if not data_path.exists():
            print(f"Sample data file not found: {data_path}")
            print("\nPlease provide either:")
            print("  - A folder path containing multiple Excel files")
            print("  - A single Excel file path")
            print("\nExamples:")
            print("  - data/test_yearly_forecast.xlsx (single file)")
            print("  - data/excel_files/ (folder with multiple Excel files)")
            return
    
    # If it's a file, use it directly
    else:
        print(f"\n📄 Single file mode: {data_path}")
    
    print(f"\nData file: {data_path}")
    
    # Create forecast configuration
    config = ForecastConfig(
        data_path=data_path.resolve(),
        forecast_years=3,           # Forecast 3 years ahead
        min_observations=3,          # Require at least 3 years of data
        model_type='arima',          # Use ARIMA models
        visualize=False,             # Set to True to generate plots
        aggregation_mode='yearly',   # Yearly aggregation
        parallel_processing=True,    # Enable parallel processing
        num_workers=4,               # Use 4 workers
        round_forecasts=True         # Round forecasts to integers
    )
    
    # Initialize and run forecaster
    try:
        forecaster = ProductCustomerForecaster(config)
        forecaster.run()
        
        print("\n" + "=" * 80)
        print("✓ FORECASTING COMPLETE!")
        print("=" * 80)
        print(f"\nResults saved to: outputs/product_customer_forecasts/")
        print("  - consolidated_forecasts.xlsx (Main Excel report)")
        print("  - forecast_summary.csv (Quick CSV summary)")
        print("  - models/ (Saved ARIMA models)")
        print("  - metadata/ (Model parameters and metrics)")
        
    except Exception as e:
        print(f"\n✗ Forecasting failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
