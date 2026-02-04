import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

def generate_dummy_data(
    num_records=10000,
    num_products=50,
    num_customers=100,
    start_year=2020,
    end_year=2024,
    output_file="data/dummy_product_customer_data.xlsx"
):
    """
    Generates dummy data for product customer forecasting.
    """
    print(f"Generating {num_records} records...")

    # Generate Products and Customers
    products = [f"Product_{i}" for i in range(1, num_products + 1)]
    customers = [f"CUST_{i:03d}" for i in range(1, num_customers + 1)]
    categories = ["Electronics", "Clothing", "Home", "Books", "Toys"]

    data = []
    
    # Generate records
    for _ in range(num_records):
        year = random.randint(start_year, end_year)
        month = random.randint(1, 12)
        product = random.choice(products)
        customer = random.choice(customers)
        category = random.choice(categories) # Just random for now
        
        # Quantity with some randomness but positive
        # Base quantity + random variation
        quantity = int(np.random.normal(loc=20, scale=10)) 
        quantity = max(1, quantity) # Ensure at least 1

        data.append({
            "Year": year,
            "Month": month,
            "Product Category": category,
            "Product": product,
            "CustomerID": customer,
            "Quantity": quantity
        })

    df = pd.DataFrame(data)
    
    # Sort by Year, Month, Product, Customer for better readability
    df = df.sort_values(by=["Year", "Month", "Product", "CustomerID"])

    print(f"Saving to {output_file}...")
    df.to_excel(output_file, index=False)
    print("Done!")

if __name__ == "__main__":
    generate_dummy_data()
