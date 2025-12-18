from __future__ import annotations
import warnings
from pathlib import Path
from typing import Dict, Optional

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
DATA_PATH = PROJECT_ROOT / "data" / "generated_data" / "synthetic_product_forecast.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
VIZ_DIR = OUTPUT_DIR / "visualizations"


def ensure_directories() -> None:
    """Create output directories if they don't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VIZ_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Output directories ready: {OUTPUT_DIR}, {VIZ_DIR}")


def check_gurobi_available() -> bool:
    """Check if Gurobi is installed and licensed."""
    if not GUROBI_AVAILABLE:
        print("✗ Gurobi is not installed. Install with: pip install gurobipy")
        return False
    
    try:
        # Test if we can create a model (checks license)
        with gp.Env(params={'OutputFlag': 0}) as env:
            with gp.Model(env=env) as test_model:
                pass
        print("✓ Gurobi is available and licensed")
        return True
    except Exception as e:
        print(f"✗ Gurobi license check failed: {e}")
        return False


def load_data(file_path: Path) -> pd.DataFrame:
    """Load and prepare demand data for optimization."""
    print(f"\nLoading data from: {file_path}")
    
    if file_path.suffix == ".csv":
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
    
    print(f"✓ Loaded {df.shape[0]} records")
    
    # Aggregate by time period
    df_agg = df.groupby("Time")["Number"].sum().reset_index()
    df_agg.columns = ["Time", "Demand"]
    df_agg["Time"] = pd.to_datetime(df_agg["Time"], format="%Y-%m")
    
    print(f"✓ Aggregated to {len(df_agg)} time periods")
    return df_agg


def build_optimization_model(
    demand_data: pd.DataFrame,
    forecast_periods: int = 12
) -> Optional[gp.Model]:
    """
    Build a simple Gurobi optimization model for demand planning.
    
    This is a placeholder implementation that can be extended with:
    - Inventory optimization
    - Production planning
    - Supply chain constraints
    - Cost minimization objectives
    
    Args:
        demand_data: Historical demand data
        forecast_periods: Number of periods to optimize
        
    Returns:
        Gurobi model instance or None if Gurobi unavailable
    """
    if not GUROBI_AVAILABLE:
        print("✗ Cannot build model: Gurobi not available")
        return None
    
    print(f"\nBuilding optimization model for {forecast_periods} periods...")
    
    try:
        # Create model
        model = gp.Model("demand_optimization")
        model.setParam('OutputFlag', 0)  # Suppress solver output
        
        # Example: Simple production planning variables
        # production[t] = amount to produce in period t
        production = model.addVars(
            forecast_periods,
            lb=0,
            name="production"
        )
        
        # Example: Inventory variables
        inventory = model.addVars(
            forecast_periods + 1,
            lb=0,
            name="inventory"
        )
        
        # Estimate future demand using simple moving average
        recent_demand = demand_data["Demand"].tail(12).mean()
        forecast_demand = [recent_demand] * forecast_periods
        
        # Inventory balance constraints
        model.addConstr(inventory[0] == 0, "initial_inventory")
        for t in range(forecast_periods):
            model.addConstr(
                inventory[t+1] == inventory[t] + production[t] - forecast_demand[t],
                f"balance_{t}"
            )
        
        # Example objective: Minimize production + holding costs
        production_cost = 10  # Cost per unit produced
        holding_cost = 2      # Cost per unit held in inventory
        
        model.setObjective(
            gp.quicksum(production_cost * production[t] for t in range(forecast_periods))
            + gp.quicksum(holding_cost * inventory[t] for t in range(1, forecast_periods + 1)),
            GRB.MINIMIZE
        )
        
        print("✓ Model built successfully")
        print(f"  Variables: {model.NumVars}")
        print(f"  Constraints: {model.NumConstrs}")
        
        return model
        
    except Exception as e:
        print(f"✗ Error building model: {e}")
        return None


def solve_model(model: gp.Model) -> Optional[Dict]:
    """
    Solve the optimization model and extract results.
    
    Args:
        model: Gurobi model instance
        
    Returns:
        Dictionary with solution results or None if solve failed
    """
    if model is None:
        return None
    
    print("\nSolving optimization model...")
    
    try:
        model.optimize()
        
        if model.Status == GRB.OPTIMAL:
            print("✓ Optimal solution found")
            print(f"  Objective value: {model.ObjVal:.2f}")
            
            # Extract solution
            results = {
                "status": "optimal",
                "objective": model.ObjVal,
                "production": [v.X for v in model.getVars() if "production" in v.VarName],
                "inventory": [v.X for v in model.getVars() if "inventory" in v.VarName]
            }
            
            return results
        else:
            print(f"✗ Solver status: {model.Status}")
            return None
            
    except Exception as e:
        print(f"✗ Error solving model: {e}")
        return None


def export_results(results: Dict, output_dir: Path) -> None:
    """Export optimization results to CSV."""
    if results is None:
        print("✗ No results to export")
        return
    
    print("\nExporting results...")
    
    # Create results dataframe
    df_results = pd.DataFrame({
        "Period": range(1, len(results["production"]) + 1),
        "Production": results["production"],
        "Inventory": results["inventory"][1:]  # Skip initial inventory
    })
    
    output_path = output_dir / "optimization_results.csv"
    df_results.to_csv(output_path, index=False)
    
    print(f"✓ Results saved to: {output_path}")


def main() -> None:
    """Main execution function for Gurobi optimization."""
    print("=" * 70)
    print("GUROBI OPTIMIZATION SYSTEM")
    print("=" * 70)
    
    # Check Gurobi availability
    if not check_gurobi_available():
        print("\n✗ Gurobi is required for this module.")
        print("Install: pip install gurobipy")
        print("License: https://www.gurobi.com/downloads/")
        return
    
    # Setup
    ensure_directories()
    
    # Load data
    demand_data = load_data(DATA_PATH)
    
    # Build and solve model
    model = build_optimization_model(demand_data, forecast_periods=12)
    results = solve_model(model)
    
    # Export results
    if results:
        export_results(results, OUTPUT_DIR)
        
        print("\n" + "=" * 70)
        print("OPTIMIZATION SUMMARY")
        print("=" * 70)
        print(f"Status: {results['status'].upper()}")
        print(f"Total Cost: ${results['objective']:.2f}")
        print(f"Total Production: {sum(results['production']):.0f} units")
        print(f"Avg Inventory: {np.mean(results['inventory']):.0f} units")
        print("=" * 70)
        print("\n✓ OPTIMIZATION COMPLETE!")
    else:
        print("\n✗ Optimization failed")


if __name__ == "__main__":
    main()
