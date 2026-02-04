"""
Run the optimizer on the large 10K dataset.
"""
import pandas as pd
import sys
import os

sys.path.append(os.getcwd())
from archive.g_optimiser_script import ProductDistribution


def load_large_data():
    """Load the generated 10K dataset"""
    print("Loading large dataset...")
    demand_df = pd.read_excel('data/large_dataset_10k.xlsx')
    inventory_df = pd.read_excel('data/large_inventory.xlsx')
    
    # Create month_index
    min_year = demand_df['Year'].min()
    min_month = demand_df['Month'].min()
    
    demand_df['date_temp'] = pd.to_datetime(
        demand_df['Year'].astype(str) + '-' + demand_df['Month'].astype(str) + '-01'
    )
    min_date = demand_df['date_temp'].min()
    
    demand_df['month_index'] = (demand_df['Year'] - min_date.year) * 12 + (demand_df['Month'] - min_date.month)
    
    # Prepare demand forecast
    demand_forecast = demand_df[['CustomerID', 'Product', 'month_index', 'Quantity']].copy()
    demand_forecast.columns = ['customer', 'product', 'month_index', 'quantity']
    
    months_horizon = demand_forecast['month_index'].max() + 1
    
    print(f"Loaded {len(demand_forecast)} demand records")
    print(f"Loaded {len(inventory_df)} inventory batches")
    print(f"Planning horizon: {months_horizon} months")
    
    return demand_forecast, inventory_df, months_horizon

def run_optimizer_large():
    """Run optimizer on large dataset"""
    
    # Load data
    demand_forecast, inventory_df, months = load_large_data()
    
    customers = demand_forecast['customer'].unique().tolist()
    products = demand_forecast['product'].unique().tolist()
    
    print(f"\nDataset stats:")
    print(f"  Customers: {len(customers)}")
    print(f"  Products: {len(products)}")
    print(f"  Months: {months}")
    print(f"  Total demand records: {len(demand_forecast)}")
    
    # Due to Gurobi license restrictions, we'll limit the problem size
    # Restricted license has ~2000 variable limit
    
    # Reduce to fit within license: 3 customers × 4 products × 12 months = 144 demand points
    # This creates approximately 144 × 30 (batches) = ~4320 variables, which should fit
    MAX_MONTHS = 12
    MAX_CUSTOMERS = 3
    MAX_PRODUCTS = 4
    
    if months > MAX_MONTHS:
        print(f"\nLimiting to {MAX_MONTHS} months (from {months}) to fit license constraints...")
        demand_forecast = demand_forecast[demand_forecast['month_index'] < MAX_MONTHS]
        months = MAX_MONTHS
    
    # Limit customers
    selected_customers = customers[:MAX_CUSTOMERS]
    demand_forecast = demand_forecast[demand_forecast['customer'].isin(selected_customers)]
    
    # Limit products
    selected_products = products[:MAX_PRODUCTS]
    demand_forecast = demand_forecast[demand_forecast['product'].isin(selected_products)]
        
    # Filter inventory
    inventory_df = inventory_df[
        (inventory_df['product'].isin(selected_products)) &
        ((inventory_df['available_month_index'] < MAX_MONTHS) | 
         (inventory_df['expiry_month_index'] > 0))
    ]
    
    # Update customer and product lists
    customers = selected_customers
    products = selected_products
    
    print(f"\nAfter filtering:")
    print(f"  Demand records: {len(demand_forecast)}")
    print(f"  Inventory batches: {len(inventory_df)}")
    
    # Check if WLS credentials are available
    use_wls = 'GUROBI_WLSACCESSID' in os.environ
    
    print(f"\nInitializing optimizer...")
    print(f"  Using WLS: {use_wls}")
    
    try:
        optimizer = ProductDistribution(
            customer=customers,
            product=products,
            months=months,
            inventory_df=inventory_df,
            demand_forecast=demand_forecast,
            penalty=100.0,
            scrap_cost_per_unit=1.0,
            use_wls=use_wls,
            verbose=True
        )
        
        print("\nRunning optimization...")
        print("This may take a few minutes for the large dataset...\n")
        
        best_dist, cost_details = optimizer.optimize_distribution()
        
        print("\n" + "="*60)
        print("OPTIMIZATION SUCCESSFUL!")
        print("="*60)
        
        # Display summary
        totals_row = cost_details[cost_details['Customer'] == 'TOTALS']
        if not totals_row.empty:
            switch_cost = totals_row['SwitchPenalty'].values[0]
            scrap_cost = totals_row['ScrapCost'].values[0]
            total_cost = switch_cost + scrap_cost
            
            print(f"\nCost Summary:")
            print(f"  Switching Cost: ${switch_cost:,.2f}")
            print(f"  Scrap Cost:     ${scrap_cost:,.2f}")
            print(f"  Total Cost:     ${total_cost:,.2f}")
        
        # Save results
        output_file = 'optimization_results_10k.xlsx'
        cost_details.to_excel(output_file, index=False)
        print(f"\nDetailed results saved to: {output_file}")
        
        # Save distribution plan
        import json
        with open('distribution_plan_10k.json', 'w') as f:
            # Convert to serializable format
            plan_serializable = {}
            for cust, months_data in best_dist.items():
                plan_serializable[cust] = {}
                for month, products in months_data.items():
                    plan_serializable[cust][str(month)] = {
                        prod: [batch, float(qty)] for prod, (batch, qty) in products.items()
                    }
            json.dump(plan_serializable, f, indent=2)
        
        print(f"Distribution plan saved to: distribution_plan_10k.json")
        
    except Exception as e:
        print(f"\nOptimization failed: {e}")
        import traceback
        traceback.print_exc()
        
        if "Model too large" in str(e) or "size-limited" in str(e):
            print("\n⚠️  The model is too large for the free Gurobi license.")
            print("   Consider:")
            print("   - Reducing the number of months further")
            print("   - Reducing the number of customers or products")
            print("   - Getting a full Gurobi license")

if __name__ == "__main__":
    run_optimizer_large()
