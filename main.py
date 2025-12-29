"""Main entry point for the ARIMA forecasting system.

Usage:
    python main.py
    
This runs the Product-Customer-Category forecasting system.
"""

from src.models.product_customer_forecast import main as run_forecast


if __name__ == "__main__":
    run_forecast()
