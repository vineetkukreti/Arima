"""Main entry point for the forecasting and optimization system.

This script allows selection between different modeling approaches:
- ARIMA: Time series forecasting using statistical methods
- Gurobi: Optimization-based demand planning (requires gurobipy)

Usage:
    python main.py              # Run ARIMA forecast (default)
    python main.py --model arima
    python main.py --model gurobi
"""

import argparse
import sys

from src.models.arima_forecast import main as run_arima_forecast


def run_gurobi_optimizer():
    """Run the Gurobi optimization workflow."""
    try:
        from src.models.gurobi_optimizer import main as run_gurobi
        run_gurobi()
    except ImportError as e:
        print(f"✗ Error importing Gurobi optimizer: {e}")
        print("\nTo use Gurobi optimization:")
        print("1. Install gurobipy: pip install gurobipy")
        print("2. Obtain a license: https://www.gurobi.com/downloads/")
        sys.exit(1)


def main():
    """Entry point with model selection."""
    parser = argparse.ArgumentParser(
        description="Forecasting and Optimization System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run ARIMA (default)
  python main.py --model arima      # Run ARIMA explicitly
  python main.py --model gurobi     # Run Gurobi optimization
        """
    )
    
    parser.add_argument(
        "--model",
        type=str,
        choices=["arima", "gurobi"],
        default="arima",
        help="Model to run: 'arima' (default) or 'gurobi'"
    )
    
    args = parser.parse_args()
    
    print(f"\n{'='*70}")
    print(f"Running {args.model.upper()} Model")
    print(f"{'='*70}\n")
    
    if args.model == "arima":
        run_arima_forecast()
    elif args.model == "gurobi":
        run_gurobi_optimizer()


if __name__ == "__main__":
    main()
