import os
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_data(num_facts=10_000_000, seed=42):
    np.random.seed(seed)
    os.makedirs("data", exist_ok=True)
    print(f"Generating deterministic synthetic dataset (Fact Rows: {num_facts:,})...")

    # 1. Dimensions
    num_customers = 100_000
    num_products = 10_000
    num_stores = 500

    # dim_customer
    segments = ['Consumer', 'Corporate', 'Home Office', 'Enterprise']
    countries = ['USA', 'Canada', 'UK', 'Germany', 'Azerbaijan', 'Japan']
    cust_df = pd.DataFrame({
        'customer_id': np.arange(1, num_customers + 1),
        'first_name': [f"First_{i}" for i in range(1, num_customers + 1)],
        'last_name': [f"Last_{i}" for i in range(1, num_customers + 1)],
        'email': [f"user_{i}@example.com" for i in range(1, num_customers + 1)],
        'segment': np.random.choice(segments, num_customers),
        'country': np.random.choice(countries, num_customers, p=[0.4, 0.2, 0.15, 0.1, 0.1, 0.05])
    })
    cust_df.to_csv("data/dim_customer.csv", index=False)

    # dim_product
    categories = ['Electronics', 'Clothing', 'Home & Kitchen', 'Books', 'Sports']
    brands = ['Acro', 'Logi', 'Apex', 'Titan', 'Zenith']
    prod_df = pd.DataFrame({
        'product_id': np.arange(1, num_products + 1),
        'product_name': [f"Product_{i}" for i in range(1, num_products + 1)],
        'category': np.random.choice(categories, num_products),
        'brand': np.random.choice(brands, num_products),
        'unit_cost': np.round(np.random.uniform(5.0, 500.0, num_products), 2)
    })
    prod_df.to_csv("data/dim_product.csv", index=False)

    # dim_store
    regions = ['North', 'South', 'East', 'West', 'Central']
    store_df = pd.DataFrame({
        'store_id': np.arange(1, num_stores + 1),
        'store_name': [f"Store_Branch_{i}" for i in range(1, num_stores + 1)],
        'city': [f"City_{i % 50}" for i in range(1, num_stores + 1)],
        'state': [f"State_{i % 20}" for i in range(1, num_stores + 1)],
        'region': np.random.choice(regions, num_stores)
    })
    store_df.to_csv("data/dim_store.csv", index=False)

    # dim_date (3 Years: 2023 to 2025)
    start_date = datetime(2023, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(1095)]
    date_df = pd.DataFrame({
        'date_key': [int(d.strftime('%Y%m%d')) for d in dates],
        'full_date': [d.strftime('%Y-%m-%d') for d in dates],
        'year': [d.year for d in dates],
        'quarter': [(d.month - 1) // 3 + 1 for d in dates],
        'month': [d.month for d in dates],
        'day_of_week': [d.isoweekday() for d in dates]
    })
    date_df.to_csv("data/dim_date.csv", index=False)

    # 2. Fact Table Generation (Chunked to keep memory lean)
    date_keys = date_df['date_key'].values
    chunk_size = 2_000_000
    fact_file = "data/fact_sales.csv"

    if os.path.exists(fact_file):
        os.remove(fact_file)

    print("Generating fact_sales chunks...")
    for chunk_idx in range(num_facts // chunk_size):
        offset = chunk_idx * chunk_size
        orders = np.arange(offset + 1, offset + chunk_size + 1)
        
        # Exponential distribution for power-law skew in customers and products
        cust_ids = np.random.choice(cust_df['customer_id'].values, chunk_size)
        prod_ids = np.random.choice(prod_df['product_id'].values, chunk_size)
        store_ids = np.random.choice(store_df['store_id'].values, chunk_size)
        d_keys = np.random.choice(date_keys, chunk_size)
        
        quantities = np.random.randint(1, 15, chunk_size)
        prices = np.round(np.random.uniform(10.0, 750.0, chunk_size), 2)
        discounts = np.round(prices * np.random.uniform(0.0, 0.25, chunk_size), 2)
        
        # Random timestamp within day
        random_seconds = np.random.randint(0, 86400, chunk_size)
        base_timestamps = pd.to_datetime(d_keys.astype(str), format='%Y%m%d')
        timestamps = (base_timestamps + pd.to_timedelta(random_seconds, unit='s')).strftime('%Y-%m-%d %H:%M:%S')

        fact_chunk = pd.DataFrame({
            'order_id': orders,
            'customer_id': cust_ids,
            'product_id': prod_ids,
            'store_id': store_ids,
            'date_key': d_keys,
            'order_timestamp': timestamps,
            'quantity': quantities,
            'unit_price': prices,
            'discount_amount': discounts
        })

        fact_chunk.to_csv(fact_file, mode='a', header=(chunk_idx == 0), index=False)
        print(f"  Processed {offset + chunk_size:,} / {num_facts:,} rows...")

    print("Data generation complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=10_000_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate_data(args.rows, args.seed)