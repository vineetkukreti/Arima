"""
Generate a large dataset with 10,000 demand data points for testing the optimizer.
"""
import pandas as pd
import numpy as np

def generate_large_dataset(num_customers=10, num_products=10, num_months=100):
    """
    Generate 10K demand data points.
    
    Parameters:
    - num_customers: 10
    - num_products: 10  
    - num_months: 100
    Total: 10 × 10 × 100 = 10,000 data points
    """
    np.random.seed(42)  # For reproducibility
    
    data = []
    
    for customer_idx in range(num_customers):
        customer_id = f"CUST_{customer_idx+1:03d}"
        
        for product_idx in range(num_products):
            product_id = f"Product_{chr(65+product_idx)}"  # Product_A, Product_B, etc.
            
            # Generate base demand with trend and seasonality
            base_demand = 50 + np.random.randint(-10, 10)
            trend = 0.5  # Slight upward trend
            
            for month_idx in range(num_months):
                # Add seasonality (12-month cycle)
                seasonal_factor = 1 + 0.2 * np.sin(2 * np.pi * month_idx / 12)
                
                # Calculate demand with noise
                demand = base_demand + (trend * month_idx) + (base_demand * seasonal_factor * 0.1)
                demand += np.random.normal(0, 5)  # Add noise
                demand = max(1, demand)  # Ensure positive
                
                # Calculate year and month from month_index
                year = 2021 + (month_idx // 12)
                month = (month_idx % 12) + 1
                
                data.append({
                    'Year': year,
                    'Month': month,
                    'Product Category': f'Category_{product_idx % 3 + 1}',
                    'Product': product_id,
                    'CustomerID': customer_id,
                    'Quantity': round(demand, 2)
                })
    
    df = pd.DataFrame(data)
    print(f"Generated {len(df)} demand records")
    print(f"Customers: {df['CustomerID'].nunique()}")
    print(f"Products: {df['Product'].nunique()}")
    print(f"Time range: {df['Year'].min()}-{df['Year'].max()}")
    
    return df

def generate_large_inventory(products, num_batches_per_product=5):
    """
    Generate inventory with multiple batches per product.
    """
    inventory_list = []
    
    for prod in products:
        for batch_idx in range(num_batches_per_product):
            # Stagger availability and expiry
            available_month = batch_idx * 20  # Batches become available every 20 months
            expiry_months = np.random.randint(15, 30)  # Batches last 15-30 months
            
            inventory_list.append({
                'batch': f'BATCH_{prod}_{batch_idx+1:02d}',
                'product': prod,
                'quantity': np.random.randint(500, 1500),
                'available_month_index': available_month,
                'expiry_month_index': available_month + expiry_months
            })
    
    return pd.DataFrame(inventory_list)

if __name__ == "__main__":
    print("Generating large dataset with 10,000 data points...")
    
    # Generate demand
    demand_df = generate_large_dataset(
        num_customers=10,
        num_products=10,
        num_months=100
    )
    
    # Save to Excel
    output_file = 'data/large_dataset_10k.xlsx'
    demand_df.to_excel(output_file, index=False)
    print(f"\nSaved to {output_file}")
    
    # Generate inventory
    products = demand_df['Product'].unique().tolist()
    inventory_df = generate_large_inventory(products, num_batches_per_product=5)
    
    inventory_file = 'data/large_inventory.xlsx'
    inventory_df.to_excel(inventory_file, index=False)
    print(f"Saved inventory to {inventory_file}")
    
    print(f"\n{'='*50}")
    print("Dataset Summary:")
    print(f"{'='*50}")
    print(f"Total demand records: {len(demand_df)}")
    print(f"Customers: {demand_df['CustomerID'].nunique()}")
    print(f"Products: {demand_df['Product'].nunique()}")
    print(f"Total inventory batches: {len(inventory_df)}")
    print(f"\nSample demand data:")
    print(demand_df.head(10))
    print(f"\nSample inventory data:")
    print(inventory_df.head(10))
