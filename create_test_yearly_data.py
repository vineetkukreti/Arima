import pandas as pd
import numpy as np

# Create sample yearly data for testing
np.random.seed(42)

data = []
years = list(range(2019, 2025))  # 2019-2024 (6 years)
products = ['ProductA', 'ProductB', 'ProductC']
customers = ['Customer1', 'Customer2', 'Customer3']
categories = ['Category1', 'Category2']

for product in products:
    for customer in customers:
        category = np.random.choice(categories)
        base = np.random.randint(100, 500)
        
        for year in years:
            quantity = base + np.random.randint(-50, 100) + (year - 2019) * np.random.randint(5, 20)
            quantity = max(0, quantity)  # Ensure non-negative
            
            data.append({
                'Year': year,
                'Product': product,
                'CustomerID': customer,
                'Product Category': category,
                'Quantity': quantity
            })

df = pd.DataFrame(data)
df.to_excel('data/test_yearly_forecast.xlsx', index=False)
print(f"Created test dataset with {len(df)} records")
print(f"\nColumns: {df.columns.tolist()}")
print(f"\nSample data:")
print(df.head(15))
print(f"\nYears: {sorted(df['Year'].unique())}")
print(f"Products: {df['Product'].nunique()}")
print(f"Customers: {df['CustomerID'].nunique()}")
