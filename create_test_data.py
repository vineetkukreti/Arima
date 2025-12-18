"""Generate synthetic test data for Product-Customer-Category forecasting.

Creates a small test dataset with:
- 5 Products
- 3 Customers  
- 2 Product Categories
- 36 months of historical data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Set random seed for reproducibility
np.random.seed(42)

# Configuration
NUM_PRODUCTS = 5
NUM_CUSTOMERS = 3
CATEGORIES = ['Electronics', 'Hardware']
START_YEAR = 2021
START_MONTH = 1
NUM_MONTHS = 36

# Generate data
data = []

for product_num in range(1, NUM_PRODUCTS + 1):
    for customer_num in range(1, NUM_CUSTOMERS + 1):
        for category in CATEGORIES:
            # Generate time series with trend and seasonality
            base_quantity = np.random.randint(50, 200)
            trend = np.random.uniform(-2, 3)
            
            for month_offset in range(NUM_MONTHS):
                year = START_YEAR + (START_MONTH + month_offset - 1) // 12
                month = (START_MONTH + month_offset - 1) % 12 + 1
                
                # Add seasonality (annual pattern)
                seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * month / 12)
                
                # Add random noise
                noise = np.random.normal(0, 10)
                
                # Calculate quantity
                quantity = int(max(0, base_quantity + trend * month_offset * seasonal_factor + noise))
                
                data.append({
                    'Year': year,
                    'Month': month,
                    'Product Category': category,
                    'Product': f'Product_{chr(65 + product_num - 1)}',
                    'CustomerID': f'CUST_{str(customer_num).zfill(3)}',
                    'Quantity': quantity
                })

# Create DataFrame
df = pd.DataFrame(data)

# Save to Excel
output_path = Path(__file__).parent / 'data' / 'test_forecast_data.xlsx'
output_path.parent.mkdir(parents=True, exist_ok=True)

df.to_excel(output_path, index=False, engine='openpyxl')

print(f"✓ Test data generated successfully!")
print(f"  File: {output_path}")
print(f"  Records: {len(df)}")
print(f"  Products: {NUM_PRODUCTS}")
print(f"  Customers: {NUM_CUSTOMERS}")
print(f"  Categories: {len(CATEGORIES)}")
print(f"  Combinations: {NUM_PRODUCTS * NUM_CUSTOMERS * len(CATEGORIES)}")
print(f"  Time range: {START_YEAR}-{START_MONTH:02d} to {df['Year'].max()}-{df['Month'].max():02d}")
