"""Generate 10,000 records for product-customer forecasting.

This script creates a synthetic dataset with:
- 50 unique products
- 200 unique customers
- 10 years of historical data (2015-2024)
- 10,000 total records
- Realistic demand patterns with trends and seasonality
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Set random seed for reproducibility
np.random.seed(42)

# Configuration
NUM_PRODUCTS = 50
NUM_CUSTOMERS = 200
START_YEAR = 2015
END_YEAR = 2024
TARGET_RECORDS = 10000

# Generate product and customer IDs
products = [f"PROD_{str(i).zfill(4)}" for i in range(1, NUM_PRODUCTS + 1)]
customers = [f"CUST_{str(i).zfill(4)}" for i in range(1, NUM_CUSTOMERS + 1)]

print("=" * 80)
print("GENERATING 10K DATASET FOR PRODUCT-CUSTOMER FORECASTING")
print("=" * 80)
print(f"Products: {NUM_PRODUCTS}")
print(f"Customers: {NUM_CUSTOMERS}")
print(f"Years: {START_YEAR}-{END_YEAR} ({END_YEAR - START_YEAR + 1} years)")
print(f"Target Records: {TARGET_RECORDS}")
print()

# Calculate distribution
years = list(range(START_YEAR, END_YEAR + 1))
records_per_year = TARGET_RECORDS // len(years)

# Generate data
data_records = []

for year in years:
    # Determine how many records for this year
    if year == END_YEAR:
        # Last year gets remaining records
        num_records = TARGET_RECORDS - len(data_records)
    else:
        num_records = records_per_year
    
    for _ in range(num_records):
        # Randomly select product and customer
        product = np.random.choice(products)
        customer = np.random.choice(customers)
        
        # Generate quantity with realistic patterns
        # Base demand varies by product (some products are more popular)
        product_idx = int(product.split('_')[1])
        base_demand = 100 + (product_idx % 20) * 50
        
        # Add year trend (increasing demand over time)
        year_factor = 1 + (year - START_YEAR) * 0.05
        
        # Add customer variation (some customers buy more)
        customer_idx = int(customer.split('_')[1])
        customer_factor = 0.5 + (customer_idx % 10) * 0.15
        
        # Add random noise
        noise = np.random.normal(1.0, 0.2)
        
        # Calculate final quantity
        quantity = int(base_demand * year_factor * customer_factor * noise)
        quantity = max(1, quantity)  # Ensure positive quantity
        
        data_records.append({
            'Year': year,
            'Product': product,
            'CustomerID': customer,
            'Quantity': quantity
        })

# Create DataFrame
df = pd.DataFrame(data_records)

# Print statistics
print("Dataset Statistics:")
print(f"Total Records: {len(df)}")
print(f"Unique Products: {df['Product'].nunique()}")
print(f"Unique Customers: {df['CustomerID'].nunique()}")
print(f"Year Range: {df['Year'].min()} - {df['Year'].max()}")
print(f"Quantity Range: {df['Quantity'].min()} - {df['Quantity'].max()}")
print(f"Average Quantity: {df['Quantity'].mean():.2f}")
print()

# Show sample data
print("Sample Data (first 10 records):")
print(df.head(10))
print()

# Show records per year
print("Records per Year:")
print(df['Year'].value_counts().sort_index())
print()

# Show top products by total quantity
print("Top 10 Products by Total Quantity:")
top_products = df.groupby('Product')['Quantity'].sum().sort_values(ascending=False).head(10)
print(top_products)
print()

# Save to Excel
output_path = Path(__file__).parent / 'test_data_10k.xlsx'
df.to_excel(output_path, index=False)
print(f"✓ Dataset saved to: {output_path}")

# Also save to CSV for faster loading
csv_path = Path(__file__).parent / 'test_data_10k.csv'
df.to_csv(csv_path, index=False)
print(f"✓ Dataset saved to: {csv_path}")

print()
print("=" * 80)
print("DATASET GENERATION COMPLETE!")
print("=" * 80)
print()
print("Usage:")
print("  python -m src.models.product_customer_forecast --data test_01/test_data_10k.xlsx --forecast-years 3")
