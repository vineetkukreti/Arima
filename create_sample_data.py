import pandas as pd
import numpy as np
from datetime import datetime

# Set random seed for reproducibility
np.random.seed(42)

# Generate sample data with Product-CustomerID combinations
products = ['Product_A', 'Product_B', 'Product_C']
customers = ['CUST_001', 'CUST_002', 'CUST_003', 'CUST_004']
categories = ['Electronics', 'Software', 'Hardware']

# Generate 36 months of data (3 years)
years = []
months = []
for year in [2021, 2022, 2023]:
    for month in range(1, 13):
        years.append(year)
        months.append(month)

# Create all combinations
data = []
for product in products:
    for customer in customers:
        # Each product-customer combination gets its own time series
        base_demand = np.random.randint(50, 200)
        trend = np.random.uniform(-2, 3)
        seasonality_strength = np.random.uniform(0.2, 0.5)
        
        for i, (year, month) in enumerate(zip(years, months)):
            # Add trend
            trend_component = i * trend
            
            # Add seasonality (12-month cycle)
            seasonal_component = base_demand * seasonality_strength * np.sin(2 * np.pi * month / 12)
            
            # Add random noise
            noise = np.random.normal(0, base_demand * 0.1)
            
            # Calculate quantity (ensure non-negative)
            quantity = max(0, int(base_demand + trend_component + seasonal_component + noise))
            
            # Determine category based on product
            category = categories[products.index(product)]
            
            data.append({
                'Year': year,
                'Month': month,
                'Product Category': category,
                'Product': product,
                'CustomerID': customer,
                'Quantity': quantity
            })

# Create DataFrame
df = pd.DataFrame(data)

# Save to Excel
output_path = 'data/sample_product_customer_data.xlsx'
df.to_excel(output_path, index=False)

print(f"✓ Sample data created: {output_path}")
print(f"  Total records: {len(df)}")
print(f"  Products: {len(products)}")
print(f"  Customers: {len(customers)}")
print(f"  Product-Customer combinations: {len(products) * len(customers)}")
print(f"  Time period: 36 months (2021-2023)")
print(f"\nFirst few rows:")
print(df.head(10))
