# Product Distribution Optimizer - Quick Start Guide

## Overview
The `run_optimizer_g.py` script uses Gurobi optimization to find the optimal product distribution plan that minimizes switching penalties and scrap costs while meeting customer demand.

## Prerequisites

### 1. Virtual Environment Setup
```bash
# Create virtual environment (first time only)
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/Mac
# OR
venv\Scripts\activate  # On Windows
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

## Input Data Files

The script expects two Excel files in the `data/` directory:

### `data/large_dataset_10k.xlsx` - Demand Forecast
Required columns:
- `Year` - Year of demand
- `Month` - Month of demand  
- `CustomerID` - Customer identifier
- `Product` - Product name
- `Quantity` - Demand quantity

### `data/large_inventory.xlsx` - Inventory Batches
Required columns:
- `batch` - Batch identifier
- `product` - Product name
- `quantity` - Available quantity
- `available_month_index` - Month when batch becomes available
- `expiry_month_index` - Month when batch expires

## Running the Optimizer

```bash
# Make sure virtual environment is activated
./venv/bin/python run_optimizer_g.py
```

## Output Files

After successful execution, you'll get:

1. **`optimization_results_10k.xlsx`** - Cost breakdown by customer
   - Switching penalties
   - Scrap costs
   - Batch assignments

2. **`distribution_plan_10k.json`** - Detailed distribution plan
   - Product-to-batch assignments
   - Quantities per customer per month

## Configuration

You can modify these parameters in the script:

- `MAX_MONTHS = 12` - Planning horizon (limited by Gurobi license)
- `MAX_CUSTOMERS = 3` - Number of customers to optimize
- `MAX_PRODUCTS = 4` - Number of products to optimize
- `penalty = 100.0` - Cost per product switch
- `scrap_cost_per_unit = 1.0` - Cost per unit scrapped

## License Notes

The script uses Gurobi's **restricted license** (free for academic/non-commercial use):
- Variable limit: ~2,000
- Expires: 2027-11-29
- For larger problems, you'll need a full Gurobi license

## Troubleshooting

### "Model too large" error
Reduce `MAX_MONTHS`, `MAX_CUSTOMERS`, or `MAX_PRODUCTS` to fit within license constraints.

### Import errors
Ensure the virtual environment is activated and all dependencies are installed.

### Missing data files
Verify that `data/large_dataset_10k.xlsx` and `data/large_inventory.xlsx` exist.

## Core Optimizer

The script uses `confi.py` which contains the `ProductDistribution` class with the actual Gurobi optimization logic.
