"""
Demo Inventory Optimization using PuLP (Free Alternative)

This script demonstrates the optimization concept using PuLP,
which is completely free and doesn't require a license.

Once you understand the concept, you can use the full Gurobi version
for better performance and larger problems.
"""

from pathlib import Path
import pandas as pd
import numpy as np

try:
    from pulp import *
    PULP_AVAILABLE = True
except ImportError:
    PULP_AVAILABLE = False

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "ProductForecast.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "optimization_demo"


def run_simple_optimization():
    """Run a simplified optimization demo using PuLP."""
    
    print("="*70)
    print("INVENTORY OPTIMIZATION DEMO (Using PuLP - Free)")
    print("="*70)
    
    if not PULP_AVAILABLE:
        print("\n✗ PuLP is not installed.")
        print("Install with: pip install pulp")
        return
    
    print("\n✓ PuLP is available (no license needed!)")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load data
    print(f"\nLoading data from: {DATA_PATH}")
    df = pd.read_excel(DATA_PATH)
    print(f"✓ Loaded {len(df)} records")
    
    # Convert time to datetime
    df['Time'] = pd.to_datetime(df['Time'], format='%Y-%m')
    
    # Aggregate demand by product and time
    df['ProductID'] = df['ItemCode'].astype(str) + '_' + df['ITemCategory'].astype(str)
    
    demand_agg = df.groupby(['ProductID', 'Time'])['Number'].sum().reset_index()
    demand_agg.columns = ['ProductID', 'Time', 'Demand']
    
    # Get unique products and time periods
    products = sorted(demand_agg['ProductID'].unique())
    time_periods = sorted(demand_agg['Time'].unique())
    
    # Limit to first 6 products and 6 time periods for demo
    products = products[:6]
    time_periods = time_periods[:6]
    
    print(f"\nOptimizing for:")
    print(f"  Products: {len(products)}")
    print(f"  Time periods: {len(time_periods)}")
    
    # Create demand dictionary
    demand = {}
    for p in products:
        demand[p] = {}
        for t, time in enumerate(time_periods):
            d = demand_agg[
                (demand_agg['ProductID'] == p) & 
                (demand_agg['Time'] == time)
            ]['Demand'].sum()
            demand[p][t] = d if d > 0 else 0
    
    # Parameters
    production_cost = 10  # Cost per unit
    holding_cost = 2      # Cost per unit per period
    ordering_cost = 500   # Fixed cost per order
    
    print(f"\nCost parameters:")
    print(f"  Production: ${production_cost}/unit")
    print(f"  Holding: ${holding_cost}/unit/period")
    print(f"  Ordering: ${ordering_cost}/order")
    
    # Create the optimization model
    print("\nBuilding optimization model...")
    model = LpProblem("Inventory_Optimization", LpMinimize)
    
    # Decision variables
    production = LpVariable.dicts("production", 
                                  [(p, t) for p in products for t in range(len(time_periods))],
                                  lowBound=0, cat='Continuous')
    
    inventory = LpVariable.dicts("inventory",
                                 [(p, t) for p in products for t in range(len(time_periods) + 1)],
                                 lowBound=0, cat='Continuous')
    
    order = LpVariable.dicts("order",
                            [(p, t) for p in products for t in range(len(time_periods))],
                            cat='Binary')
    
    # Objective: Minimize total cost
    model += (
        lpSum([production_cost * production[p, t] 
               for p in products for t in range(len(time_periods))]) +
        lpSum([holding_cost * inventory[p, t] 
               for p in products for t in range(1, len(time_periods) + 1)]) +
        lpSum([ordering_cost * order[p, t] 
               for p in products for t in range(len(time_periods))])
    )
    
    # Constraints
    # Initial inventory
    for p in products:
        model += inventory[p, 0] == 0, f"Initial_Inv_{p}"
    
    # Inventory balance
    for p in products:
        for t in range(len(time_periods)):
            model += (inventory[p, t+1] == inventory[p, t] + production[p, t] - demand[p][t],
                     f"Balance_{p}_{t}")
    
    # Production-order linking
    for p in products:
        for t in range(len(time_periods)):
            model += production[p, t] <= 10000 * order[p, t], f"Order_Link_{p}_{t}"
    
    print("✓ Model built")
    print(f"  Variables: {len(model.variables())}")
    print(f"  Constraints: {len(model.constraints)}")
    
    # Solve
    print("\nSolving...")
    solver = PULP_CBC_CMD(msg=0)  # Use CBC solver (free, open-source)
    model.solve(solver)
    
    # Check status
    status = LpStatus[model.status]
    print(f"✓ Status: {status}")
    
    if status == 'Optimal':
        print(f"✓ Optimal solution found!")
        print(f"  Total Cost: ${value(model.objective):,.2f}")
        
        # Extract results
        production_results = []
        inventory_results = []
        order_results = []
        
        for p in products:
            item_code, category = p.split('_')
            for t in range(len(time_periods)):
                # Production
                prod_qty = production[p, t].varValue
                if prod_qty > 0.01:
                    production_results.append({
                        'ItemCode': item_code,
                        'ItemCategory': category,
                        'Time': time_periods[t].strftime('%Y-%m'),
                        'Production': round(prod_qty, 2),
                        'Demand': demand[p][t],
                        'Cost': round(prod_qty * production_cost, 2)
                    })
                
                # Inventory
                inv_qty = inventory[p, t+1].varValue
                if inv_qty > 0.01:
                    inventory_results.append({
                        'ItemCode': item_code,
                        'ItemCategory': category,
                        'Time': time_periods[t].strftime('%Y-%m'),
                        'Inventory': round(inv_qty, 2),
                        'Cost': round(inv_qty * holding_cost, 2)
                    })
                
                # Orders
                if order[p, t].varValue > 0.5:
                    order_results.append({
                        'ItemCode': item_code,
                        'ItemCategory': category,
                        'Time': time_periods[t].strftime('%Y-%m'),
                        'OrderPlaced': 'Yes',
                        'Cost': ordering_cost
                    })
        
        # Export results
        print("\nExporting results...")
        
        if production_results:
            df_prod = pd.DataFrame(production_results)
            prod_file = OUTPUT_DIR / "demo_production.xlsx"
            df_prod.to_excel(prod_file, index=False)
            print(f"✓ Production: {prod_file}")
        
        if inventory_results:
            df_inv = pd.DataFrame(inventory_results)
            inv_file = OUTPUT_DIR / "demo_inventory.xlsx"
            df_inv.to_excel(inv_file, index=False)
            print(f"✓ Inventory: {inv_file}")
        
        if order_results:
            df_ord = pd.DataFrame(order_results)
            ord_file = OUTPUT_DIR / "demo_orders.xlsx"
            df_ord.to_excel(ord_file, index=False)
            print(f"✓ Orders: {ord_file}")
        
        # Summary
        total_production = sum(r['Production'] for r in production_results)
        total_demand = sum(sum(demand[p].values()) for p in products)
        
        summary = {
            'Metric': [
                'Total Cost',
                'Production Cost',
                'Holding Cost',
                'Ordering Cost',
                'Total Production',
                'Total Demand',
                'Number of Orders'
            ],
            'Value': [
                f"${value(model.objective):,.2f}",
                f"${sum(r['Cost'] for r in production_results):,.2f}",
                f"${sum(r['Cost'] for r in inventory_results):,.2f}",
                f"${sum(r['Cost'] for r in order_results):,.2f}",
                f"{total_production:,.0f} units",
                f"{total_demand:,.0f} units",
                len(order_results)
            ]
        }
        
        df_summary = pd.DataFrame(summary)
        summary_file = OUTPUT_DIR / "demo_summary.xlsx"
        df_summary.to_excel(summary_file, index=False)
        print(f"✓ Summary: {summary_file}")
        
        print("\n" + "="*70)
        print("OPTIMIZATION COMPLETE!")
        print("="*70)
        print(f"Total Cost: ${value(model.objective):,.2f}")
        print(f"Total Production: {total_production:,.0f} units")
        print(f"Total Demand: {total_demand:,.0f} units")
        print(f"Number of Orders: {len(order_results)}")
        print("="*70)
        
        print("\n💡 This is a simplified demo using PuLP (free solver)")
        print("   For larger problems and better performance, use Gurobi!")
        print("   See: src/models/inventory_optimization.py")
        
    else:
        print(f"✗ Optimization failed with status: {status}")


if __name__ == "__main__":
    run_simple_optimization()
