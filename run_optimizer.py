import pandas as pd
import numpy as np
import os
import sys

# Add current directory to path to import confi
sys.path.append(os.getcwd())

try:
    from confi import ProductDistribution
except ImportError:
    print("Error: Could not import ProductDistribution from confi.py")
    sys.exit(1)

def load_and_prepare_data(filepath):
    """
    Loads Excel data and prepares it for the optimizer.
    """
    print(f"Loading data from {filepath}...")
    df = pd.read_excel(filepath)
    
    # Basic cleaning
    df = df.dropna(subset=['Product', 'CustomerID', 'Quantity'])
    
    # Create Month Index
    # Assuming data spans multiple years, we need a continuous month index
    # Find min year and month to establish start
    min_year = df['Year'].min()
    min_month = df['Month'].min()
    
    print(f"Data range: Year {min_year}-{df['Year'].max()}")
    
    # Calculate month_index: (Year - MinYear) * 12 + (Month - 1)
    # Adjusting so the first month in data is index 0
    # If Month is 1-based (1=Jan)
    
    # Handling the case where Month might be missing (Yearly variant question)
    if 'Month' not in df.columns or df['Month'].isnull().all():
        print("Detected Yearly data (no Month column or all nulls). Treating Years as time periods.")
        # Treat each Year as a step
        df['month_index'] = df['Year'] - min_year
        months_horizon = df['month_index'].max() + 1
    else:
        # Standard Monthly data
        # Normalize month to 1-12 just in case
        df['Month'] = df['Month'].fillna(1).astype(int)
        
        # Calculate absolute month index from start of dataset
        # We'll assume the dataset starts at min_year, month 1 for simplicity of index 0
        # Or strictly based on min_month
        
        # Let's use a standard (Year-MinYear)*12 + (Month-1) approach
        # But we want the earliest date to be 0.
        
        # Construct a datetime to easily sort and find min
        df['date_temp'] = pd.to_datetime(df['Year'].astype(str) + '-' + df['Month'].astype(str) + '-01')
        min_date = df['date_temp'].min()
        
        def get_month_index(row):
            return (row['Year'] - min_date.year) * 12 + (row['Month'] - min_date.month)
            
        df['month_index'] = df.apply(get_month_index, axis=1)
        months_horizon = df['month_index'].max() + 1
        
    print(f"Planning Horizon: {months_horizon} months")
    
    # Prepare demand_forecast DataFrame
    # Columns required: customer, product, month_index, quantity
    demand_forecast = df[['CustomerID', 'Product', 'month_index', 'Quantity']].copy()
    demand_forecast.columns = ['customer', 'product', 'month_index', 'quantity']
    
    # Aggregate duplicates if any
    demand_forecast = demand_forecast.groupby(['customer', 'product', 'month_index'], as_index=False)['quantity'].sum()
    
    # Scale down demand to force usage of our small realistic batches
    # Original demand is ~150-200/month, our batches are 150/400.
    # We want them to use the batches and switch.
    print("Scaling down demand by factor of 20 to match realistic inventory size...")
    demand_forecast['quantity'] = demand_forecast['quantity'] / 20.0
    
    # Limit to 12 months to fit in restricted Gurobi license if needed
    # The full 36 months exceeds the 2000 variable/constraint limit of the free license
    MAX_MONTHS = 12
    if months_horizon > MAX_MONTHS:
        print(f"Limiting horizon from {months_horizon} to {MAX_MONTHS} months to fit restricted license.")
        months_horizon = MAX_MONTHS
        demand_forecast = demand_forecast[demand_forecast['month_index'] < MAX_MONTHS]
    
    return demand_forecast, months_horizon

def generate_dummy_inventory(products, quantity=1000):
    """
    Generates realistic inventory with multiple batches, varying quantities,
    and expiry dates to force optimizer decisions.
    """
    inventory_list = []
    
    # Create mixed batches that contain ALL products
    # This is required because the model enforces one master batch per customer/month
    
    # Batch 1: OLD (Expires month 5)
    for prod in products:
        inventory_list.append({
            'batch': 'BATCH_OLD',
            'product': prod,
            'quantity': 200,
            'available_month_index': 0,
            'expiry_month_index': 5
        })
        
    # Batch 2: MAIN (Expires month 11)
    for prod in products:
        inventory_list.append({
            'batch': 'BATCH_MAIN',
            'product': prod,
            'quantity': 200,
            'available_month_index': 0,
            'expiry_month_index': 11
        })
        
    # Batch 3: NEW (Available month 3)
    for prod in products:
        inventory_list.append({
            'batch': 'BATCH_NEW',
            'product': prod,
            'quantity': 500,
            'available_month_index': 3,
            'expiry_month_index': 24
        })
        
    return pd.DataFrame(inventory_list)

def main():
    data_path = 'data/sample_product_customer_data.xlsx'
    
    if not os.path.exists(data_path):
        print(f"File not found: {data_path}")
        return

    # 1. Load and Transform Demand
    demand_forecast, months = load_and_prepare_data(data_path)
    
    unique_customers = demand_forecast['customer'].unique().tolist()
    unique_products = demand_forecast['product'].unique().tolist()
    
    print(f"Customers: {len(unique_customers)}")
    print(f"Products: {len(unique_products)}")
    
    # 2. Generate Inventory
    print("Generating dummy inventory (1000 units per product)...")
    inventory_df = generate_dummy_inventory(unique_products, quantity=1000)
    
    # 3. Setup Optimizer
    print("Initializing Optimizer...")
    
    # Note: Gurobi might require a license. 
    # If WLS is used, credentials are needed. 
    # For this test, we'll try with use_wls=False to use local license if available,
    # or rely on the class defaults if env vars are set.
    
    # Check if we have WLS credentials in env, otherwise try local
    use_wls = 'GUROBI_WLSACCESSID' in os.environ
    
    try:
        optimizer = ProductDistribution(
            customer=unique_customers,
            product=unique_products,
            months=months,
            inventory_df=inventory_df,
            demand_forecast=demand_forecast,
            use_wls=use_wls, 
            verbose=True
        )
        
        print("Running optimization...")
        best_dist, cost_details = optimizer.optimize_distribution()
        
        print("\nOptimization Successful!")
        print("-" * 30)
        print("Cost Summary:")
        print(cost_details[cost_details['Customer'] == 'TOTALS'].to_string(index=False))
        
        # Save results
        output_file = 'optimization_results.csv'
        cost_details.to_csv(output_file, index=False)
        print(f"\nDetailed results saved to {output_file}")
        
    except Exception as e:
        print(f"\nExecution failed: {e}")
        print("\nNote: This error is likely due to missing Gurobi license or credentials.")
        print("To run this successfully, ensure you have a valid Gurobi license.")

if __name__ == "__main__":
    main()
