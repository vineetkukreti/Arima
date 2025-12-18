"""
Inventory Optimization using Gurobi

This script performs multi-product inventory optimization considering:
- Customer demand patterns (CustID)
- Product characteristics (ItemCode, ItemCategory)
- Time-series demand (Time, Number)
- Inventory holding costs
- Production/ordering costs
- Service level constraints
"""

from __future__ import annotations
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

try:
    import gurobipy as gp
    from gurobipy import GRB
    GUROBI_AVAILABLE = True
except ImportError:
    GUROBI_AVAILABLE = False
    gp = None
    GRB = None

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "ProductForecast.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "optimization"


class InventoryOptimizer:
    """
    Multi-product inventory optimization using Gurobi.
    
    Optimizes inventory levels, production quantities, and ordering decisions
    to minimize total costs while meeting demand and service level requirements.
    """
    
    def __init__(
        self,
        data_path: Path = DATA_PATH,
        output_dir: Path = OUTPUT_DIR,
        planning_horizon: int = 12
    ):
        """
        Initialize the optimizer.
        
        Args:
            data_path: Path to input data file
            output_dir: Directory for output files
            planning_horizon: Number of periods to optimize (months)
        """
        self.data_path = data_path
        self.output_dir = output_dir
        self.planning_horizon = planning_horizon
        self.df_raw = None
        self.df_processed = None
        self.model = None
        self.results = {}
        
        # Cost parameters (can be customized)
        self.holding_cost_rate = 0.15  # 15% annual holding cost
        self.ordering_cost = 500  # Fixed cost per order
        self.production_cost_base = 10  # Base production cost per unit
        self.stockout_penalty = 50  # Penalty per unit of unmet demand
        
        # Constraints
        self.min_service_level = 0.95  # 95% service level
        self.max_inventory_capacity = 10000  # Maximum warehouse capacity
        
    def ensure_directories(self) -> None:
        """Create output directories if they don't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Output directory ready: {self.output_dir}")
    
    def check_gurobi(self) -> bool:
        """Check if Gurobi is available and licensed."""
        if not GUROBI_AVAILABLE:
            print("✗ Gurobi is not installed. Install with: pip install gurobipy")
            return False
        
        try:
            with gp.Env(params={'OutputFlag': 0}) as env:
                with gp.Model(env=env) as test_model:
                    pass
            print("✓ Gurobi is available and licensed")
            return True
        except Exception as e:
            print(f"✗ Gurobi license check failed: {e}")
            print("  Get a free academic license: https://www.gurobi.com/academia/")
            return False
    
    def load_and_process_data(self) -> pd.DataFrame:
        """
        Load and process the input data.
        
        Returns:
            Processed DataFrame with demand data
        """
        print(f"\n{'='*70}")
        print("LOADING DATA")
        print(f"{'='*70}")
        print(f"Reading: {self.data_path}")
        
        # Load data
        if self.data_path.suffix == ".csv":
            self.df_raw = pd.read_csv(self.data_path)
        else:
            self.df_raw = pd.read_excel(self.data_path)
        
        print(f"✓ Loaded {len(self.df_raw)} records")
        print(f"  Columns: {self.df_raw.columns.tolist()}")
        
        # Process data
        df = self.df_raw.copy()
        
        # Convert Time to datetime
        df['Time'] = pd.to_datetime(df['Time'], format='%Y-%m')
        
        # Sort by time
        df = df.sort_values('Time')
        
        # Create unique product identifier
        df['ProductID'] = df['ItemCode'].astype(str) + '_' + df['ITemCategory'].astype(str)
        
        # Summary statistics
        print(f"\n{'='*70}")
        print("DATA SUMMARY")
        print(f"{'='*70}")
        print(f"Time range: {df['Time'].min()} to {df['Time'].max()}")
        print(f"Unique customers: {df['CUSTID'].nunique()}")
        print(f"Unique item codes: {df['ItemCode'].nunique()}")
        print(f"Unique categories: {df['ITemCategory'].nunique()}")
        print(f"Unique products: {df['ProductID'].nunique()}")
        print(f"Total demand: {df['Number'].sum():,.0f} units")
        print(f"Average demand per record: {df['Number'].mean():.2f} units")
        
        self.df_processed = df
        return df
    
    def prepare_optimization_data(self) -> Dict:
        """
        Prepare data structures for optimization.
        
        Returns:
            Dictionary containing optimization parameters
        """
        print(f"\n{'='*70}")
        print("PREPARING OPTIMIZATION DATA")
        print(f"{'='*70}")
        
        df = self.df_processed
        
        # Get unique products and time periods
        products = sorted(df['ProductID'].unique())
        customers = sorted(df['CUSTID'].unique())
        time_periods = sorted(df['Time'].unique())
        
        # Limit to planning horizon
        if len(time_periods) > self.planning_horizon:
            time_periods = time_periods[-self.planning_horizon:]
            df = df[df['Time'].isin(time_periods)]
        
        # Create demand matrix: demand[product][time][customer]
        demand_dict = {}
        for product in products:
            demand_dict[product] = {}
            for t, time in enumerate(time_periods):
                demand_dict[product][t] = {}
                for customer in customers:
                    demand = df[
                        (df['ProductID'] == product) & 
                        (df['Time'] == time) & 
                        (df['CUSTID'] == customer)
                    ]['Number'].sum()
                    demand_dict[product][t][customer] = demand
        
        # Calculate total demand per product per period
        total_demand = {}
        for product in products:
            total_demand[product] = {}
            for t in range(len(time_periods)):
                total_demand[product][t] = sum(demand_dict[product][t].values())
        
        # Calculate product-specific costs based on category
        product_costs = {}
        for product in products:
            category = int(product.split('_')[1])
            # Higher category = higher cost (example logic)
            product_costs[product] = self.production_cost_base * (1 + 0.1 * category)
        
        opt_data = {
            'products': products,
            'customers': customers,
            'time_periods': time_periods,
            'num_periods': len(time_periods),
            'demand_dict': demand_dict,
            'total_demand': total_demand,
            'product_costs': product_costs
        }
        
        print(f"✓ Products: {len(products)}")
        print(f"✓ Customers: {len(customers)}")
        print(f"✓ Time periods: {len(time_periods)}")
        print(f"✓ Total demand across all periods: {sum(sum(d.values()) for d in total_demand.values()):,.0f} units")
        
        return opt_data
    
    def build_model(self, opt_data: Dict) -> gp.Model:
        """
        Build the Gurobi optimization model.
        
        Args:
            opt_data: Optimization data dictionary
            
        Returns:
            Gurobi model instance
        """
        print(f"\n{'='*70}")
        print("BUILDING OPTIMIZATION MODEL")
        print(f"{'='*70}")
        
        products = opt_data['products']
        num_periods = opt_data['num_periods']
        total_demand = opt_data['total_demand']
        product_costs = opt_data['product_costs']
        
        # Create model
        model = gp.Model("inventory_optimization")
        model.setParam('OutputFlag', 0)  # Suppress solver output
        model.setParam('TimeLimit', 300)  # 5 minute time limit
        
        # Decision Variables
        # production[p, t] = amount to produce of product p in period t
        production = model.addVars(
            products, range(num_periods),
            lb=0,
            vtype=GRB.CONTINUOUS,
            name="production"
        )
        
        # inventory[p, t] = inventory level of product p at end of period t
        inventory = model.addVars(
            products, range(num_periods + 1),
            lb=0,
            vtype=GRB.CONTINUOUS,
            name="inventory"
        )
        
        # order[p, t] = binary variable, 1 if we order product p in period t
        order = model.addVars(
            products, range(num_periods),
            vtype=GRB.BINARY,
            name="order"
        )
        
        # stockout[p, t] = unmet demand for product p in period t
        stockout = model.addVars(
            products, range(num_periods),
            lb=0,
            vtype=GRB.CONTINUOUS,
            name="stockout"
        )
        
        print("✓ Decision variables created")
        
        # Constraints
        
        # 1. Initial inventory (assume starting with zero)
        for p in products:
            model.addConstr(inventory[p, 0] == 0, f"initial_inv_{p}")
        
        # 2. Inventory balance constraints
        for p in products:
            for t in range(num_periods):
                demand = total_demand[p][t]
                model.addConstr(
                    inventory[p, t+1] == inventory[p, t] + production[p, t] - demand + stockout[p, t],
                    f"balance_{p}_{t}"
                )
        
        # 3. Production-order linking (can only produce if we order)
        for p in products:
            for t in range(num_periods):
                model.addConstr(
                    production[p, t] <= 10000 * order[p, t],
                    f"order_link_{p}_{t}"
                )
        
        # 4. Warehouse capacity constraint
        for t in range(num_periods + 1):
            model.addConstr(
                gp.quicksum(inventory[p, t] for p in products) <= self.max_inventory_capacity,
                f"capacity_{t}"
            )
        
        # 5. Service level constraint (limit total stockouts)
        total_demand_all = sum(sum(total_demand[p].values()) for p in products)
        max_stockout = total_demand_all * (1 - self.min_service_level)
        model.addConstr(
            gp.quicksum(stockout[p, t] for p in products for t in range(num_periods)) <= max_stockout,
            "service_level"
        )
        
        print("✓ Constraints added")
        
        # Objective Function: Minimize total cost
        # Total cost = Production cost + Holding cost + Ordering cost + Stockout penalty
        
        # Production cost
        production_cost_expr = gp.quicksum(
            product_costs[p] * production[p, t]
            for p in products for t in range(num_periods)
        )
        
        # Holding cost (monthly rate = annual rate / 12)
        monthly_holding_rate = self.holding_cost_rate / 12
        holding_cost_expr = gp.quicksum(
            product_costs[p] * monthly_holding_rate * inventory[p, t]
            for p in products for t in range(1, num_periods + 1)
        )
        
        # Ordering cost
        ordering_cost_expr = gp.quicksum(
            self.ordering_cost * order[p, t]
            for p in products for t in range(num_periods)
        )
        
        # Stockout penalty
        stockout_cost_expr = gp.quicksum(
            self.stockout_penalty * stockout[p, t]
            for p in products for t in range(num_periods)
        )
        
        # Set objective
        model.setObjective(
            production_cost_expr + holding_cost_expr + ordering_cost_expr + stockout_cost_expr,
            GRB.MINIMIZE
        )
        
        print("✓ Objective function set")
        print(f"\nModel Statistics:")
        print(f"  Variables: {model.NumVars}")
        print(f"  Constraints: {model.NumConstrs}")
        print(f"  Binary variables: {sum(1 for v in model.getVars() if v.VType == GRB.BINARY)}")
        
        self.model = model
        return model
    
    def solve_model(self) -> Dict:
        """
        Solve the optimization model.
        
        Returns:
            Dictionary with solution results
        """
        print(f"\n{'='*70}")
        print("SOLVING OPTIMIZATION MODEL")
        print(f"{'='*70}")
        
        if self.model is None:
            print("✗ No model to solve")
            return {}
        
        try:
            self.model.optimize()
            
            if self.model.Status == GRB.OPTIMAL:
                print("✓ OPTIMAL SOLUTION FOUND")
                print(f"  Objective value: ${self.model.ObjVal:,.2f}")
                print(f"  Solution time: {self.model.Runtime:.2f} seconds")
                
                # Extract solution
                results = {
                    'status': 'optimal',
                    'objective': self.model.ObjVal,
                    'runtime': self.model.Runtime,
                    'variables': {}
                }
                
                # Store all variable values
                for v in self.model.getVars():
                    results['variables'][v.VarName] = v.X
                
                self.results = results
                return results
                
            elif self.model.Status == GRB.INFEASIBLE:
                print("✗ Model is infeasible")
                print("  Computing IIS (Irreducible Inconsistent Subsystem)...")
                self.model.computeIIS()
                iis_file = self.output_dir / "model_infeasible.ilp"
                self.model.write(str(iis_file))
                print(f"  IIS written to: {iis_file}")
                return {'status': 'infeasible'}
                
            elif self.model.Status == GRB.TIME_LIMIT:
                print("⚠ Time limit reached")
                if self.model.SolCount > 0:
                    print(f"  Best solution found: ${self.model.ObjVal:,.2f}")
                    print(f"  Gap: {self.model.MIPGap*100:.2f}%")
                    return {'status': 'time_limit', 'objective': self.model.ObjVal}
                else:
                    print("  No feasible solution found")
                    return {'status': 'time_limit_no_solution'}
            else:
                print(f"✗ Solver status: {self.model.Status}")
                return {'status': f'other_{self.model.Status}'}
                
        except Exception as e:
            print(f"✗ Error solving model: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def export_results(self, opt_data: Dict) -> None:
        """
        Export optimization results to Excel files.
        
        Args:
            opt_data: Optimization data dictionary
        """
        if not self.results or self.results.get('status') != 'optimal':
            print("\n✗ No optimal solution to export")
            return
        
        print(f"\n{'='*70}")
        print("EXPORTING RESULTS")
        print(f"{'='*70}")
        
        products = opt_data['products']
        num_periods = opt_data['num_periods']
        time_periods = opt_data['time_periods']
        total_demand = opt_data['total_demand']
        product_costs = opt_data['product_costs']
        variables = self.results['variables']
        
        # 1. Production Schedule
        production_data = []
        for p in products:
            item_code, category = p.split('_')
            for t in range(num_periods):
                var_name = f"production[{p},{t}]"
                production_qty = variables.get(var_name, 0)
                if production_qty > 0.01:  # Only include non-zero production
                    production_data.append({
                        'ItemCode': item_code,
                        'ItemCategory': category,
                        'Time': time_periods[t].strftime('%Y-%m'),
                        'ProductionQuantity': round(production_qty, 2),
                        'Demand': total_demand[p][t],
                        'UnitCost': product_costs[p],
                        'TotalCost': round(production_qty * product_costs[p], 2)
                    })
        
        df_production = pd.DataFrame(production_data)
        production_file = self.output_dir / "production_schedule.xlsx"
        df_production.to_excel(production_file, index=False, sheet_name='Production')
        print(f"✓ Production schedule: {production_file}")
        
        # 2. Inventory Levels
        inventory_data = []
        for p in products:
            item_code, category = p.split('_')
            for t in range(1, num_periods + 1):
                var_name = f"inventory[{p},{t}]"
                inv_level = variables.get(var_name, 0)
                if inv_level > 0.01:  # Only include non-zero inventory
                    inventory_data.append({
                        'ItemCode': item_code,
                        'ItemCategory': category,
                        'Time': time_periods[t-1].strftime('%Y-%m'),
                        'InventoryLevel': round(inv_level, 2),
                        'HoldingCost': round(inv_level * product_costs[p] * self.holding_cost_rate / 12, 2)
                    })
        
        df_inventory = pd.DataFrame(inventory_data)
        inventory_file = self.output_dir / "inventory_levels.xlsx"
        df_inventory.to_excel(inventory_file, index=False, sheet_name='Inventory')
        print(f"✓ Inventory levels: {inventory_file}")
        
        # 3. Order Schedule
        order_data = []
        for p in products:
            item_code, category = p.split('_')
            for t in range(num_periods):
                var_name = f"order[{p},{t}]"
                order_placed = variables.get(var_name, 0)
                if order_placed > 0.5:  # Binary variable
                    order_data.append({
                        'ItemCode': item_code,
                        'ItemCategory': category,
                        'Time': time_periods[t].strftime('%Y-%m'),
                        'OrderPlaced': 'Yes',
                        'OrderingCost': self.ordering_cost
                    })
        
        df_orders = pd.DataFrame(order_data)
        orders_file = self.output_dir / "order_schedule.xlsx"
        df_orders.to_excel(orders_file, index=False, sheet_name='Orders')
        print(f"✓ Order schedule: {orders_file}")
        
        # 4. Stockouts (if any)
        stockout_data = []
        for p in products:
            item_code, category = p.split('_')
            for t in range(num_periods):
                var_name = f"stockout[{p},{t}]"
                stockout_qty = variables.get(var_name, 0)
                if stockout_qty > 0.01:
                    stockout_data.append({
                        'ItemCode': item_code,
                        'ItemCategory': category,
                        'Time': time_periods[t].strftime('%Y-%m'),
                        'StockoutQuantity': round(stockout_qty, 2),
                        'Demand': total_demand[p][t],
                        'ServiceLevel': round((1 - stockout_qty / total_demand[p][t]) * 100, 2),
                        'PenaltyCost': round(stockout_qty * self.stockout_penalty, 2)
                    })
        
        if stockout_data:
            df_stockouts = pd.DataFrame(stockout_data)
            stockouts_file = self.output_dir / "stockouts.xlsx"
            df_stockouts.to_excel(stockouts_file, index=False, sheet_name='Stockouts')
            print(f"✓ Stockouts: {stockouts_file}")
        else:
            print("✓ No stockouts (100% service level achieved!)")
        
        # 5. Summary Report
        summary_data = {
            'Metric': [
                'Total Cost',
                'Production Cost',
                'Holding Cost',
                'Ordering Cost',
                'Stockout Penalty',
                'Total Production',
                'Total Demand',
                'Service Level (%)',
                'Avg Inventory',
                'Number of Orders'
            ],
            'Value': [
                f"${self.results['objective']:,.2f}",
                f"${sum(row['TotalCost'] for row in production_data):,.2f}",
                f"${sum(row['HoldingCost'] for row in inventory_data):,.2f}",
                f"${len(order_data) * self.ordering_cost:,.2f}",
                f"${sum(row['PenaltyCost'] for row in stockout_data) if stockout_data else 0:,.2f}",
                f"{sum(row['ProductionQuantity'] for row in production_data):,.0f} units",
                f"{sum(sum(total_demand[p].values()) for p in products):,.0f} units",
                f"{(1 - sum(row['StockoutQuantity'] for row in stockout_data) / sum(sum(total_demand[p].values()) for p in products)) * 100:.2f}%" if stockout_data else "100.00%",
                f"{sum(row['InventoryLevel'] for row in inventory_data) / len(inventory_data) if inventory_data else 0:.2f} units",
                len(order_data)
            ]
        }
        
        df_summary = pd.DataFrame(summary_data)
        summary_file = self.output_dir / "optimization_summary.xlsx"
        df_summary.to_excel(summary_file, index=False, sheet_name='Summary')
        print(f"✓ Summary report: {summary_file}")
        
        print(f"\n✓ All results exported to: {self.output_dir}")
    
    def run_optimization(self) -> bool:
        """
        Run the complete optimization workflow.
        
        Returns:
            True if optimization succeeded, False otherwise
        """
        print(f"\n{'='*70}")
        print("INVENTORY OPTIMIZATION WITH GUROBI")
        print(f"{'='*70}\n")
        
        # Check Gurobi
        if not self.check_gurobi():
            return False
        
        # Setup
        self.ensure_directories()
        
        # Load data
        self.load_and_process_data()
        
        # Prepare optimization data
        opt_data = self.prepare_optimization_data()
        
        # Build model
        self.build_model(opt_data)
        
        # Solve model
        results = self.solve_model()
        
        # Export results
        if results.get('status') == 'optimal':
            self.export_results(opt_data)
            
            print(f"\n{'='*70}")
            print("OPTIMIZATION COMPLETE!")
            print(f"{'='*70}")
            print(f"✓ Total cost minimized: ${results['objective']:,.2f}")
            print(f"✓ Results exported to: {self.output_dir}")
            print(f"{'='*70}\n")
            return True
        else:
            print(f"\n✗ Optimization failed with status: {results.get('status')}")
            return False


def main():
    """Main execution function."""
    optimizer = InventoryOptimizer(
        data_path=DATA_PATH,
        output_dir=OUTPUT_DIR,
        planning_horizon=12
    )
    
    success = optimizer.run_optimization()
    
    if not success:
        print("\n" + "="*70)
        print("TROUBLESHOOTING")
        print("="*70)
        print("If Gurobi is not installed:")
        print("  pip install gurobipy")
        print("\nIf you need a license:")
        print("  Academic: https://www.gurobi.com/academia/")
        print("  Free trial: https://www.gurobi.com/downloads/")
        print("="*70)


if __name__ == "__main__":
    main()
