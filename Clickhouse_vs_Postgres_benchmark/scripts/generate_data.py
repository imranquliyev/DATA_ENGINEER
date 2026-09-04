#!/usr/bin/env python3
"""
Deterministic Synthetic Data Generator for Analytical Query Benchmark
Generates Star Schema datasets (10M rows and 1M rows) with realistic skews and fixed random seed (42).
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

SEED = 42

def generate_dimensions(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    np.random.seed(SEED)
    print(f"Generating dimension tables in {output_dir}...")

    # 1. dim_date (3 Years: 2023-01-01 to 2025-12-31 = 1095 days)
    start_date = datetime(2023, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(1095)]
    date_df = pd.DataFrame({
        'date_id': [d.strftime('%Y-%m-%d') for d in dates],
        'year': [d.year for d in dates],
        'quarter': [(d.month - 1) // 3 + 1 for d in dates],
        'month': [d.month for d in dates],
        'day_of_week': [d.isoweekday() for d in dates],
        'is_weekend': [1 if d.isoweekday() in (6, 7) else 0 for d in dates]
    })
    date_df.to_csv(os.path.join(output_dir, 'dim_date.csv'), index=False)
    print(f"  dim_date: {len(date_df)} rows")

    # 2. dim_store (1,000 stores)
    num_stores = 1000
    regions = ['North', 'South', 'East', 'West']
    store_types = ['Supercenter', 'Express', 'Outlet', 'Flagship', 'Online']
    cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose']
    states = ['NY', 'CA', 'IL', 'TX', 'AZ', 'PA', 'TX', 'CA', 'TX', 'CA']
    
    store_df = pd.DataFrame({
        'store_id': np.arange(1, num_stores + 1),
        'store_name': [f"Store_{i:04d}" for i in range(1, num_stores + 1)],
        'city': np.random.choice(cities, size=num_stores),
        'state': np.random.choice(states, size=num_stores),
        'region': np.random.choice(regions, size=num_stores, p=[0.3, 0.25, 0.25, 0.2]),
        'store_type': np.random.choice(store_types, size=num_stores, p=[0.4, 0.25, 0.15, 0.1, 0.1])
    })
    store_df.to_csv(os.path.join(output_dir, 'dim_store.csv'), index=False)
    print(f"  dim_store: {len(store_df)} rows")

    # 3. dim_product (50,000 products)
    num_products = 50000
    categories = ['Electronics', 'Clothing', 'Home & Kitchen', 'Beauty', 'Sports', 'Books', 'Toys', 'Automotive', 'Grocery', 'Garden']
    brands = ['BrandA', 'BrandB', 'BrandC', 'BrandD', 'BrandE', 'BrandF', 'BrandG', 'BrandH']
    
    prod_categories = np.random.choice(categories, size=num_products)
    unit_costs = np.round(np.random.exponential(scale=40.0, size=num_products) + 2.0, 2)

    product_df = pd.DataFrame({
        'product_id': np.arange(1, num_products + 1),
        'product_name': [f"Product_{i:06d}" for i in range(1, num_products + 1)],
        'category': prod_categories,
        'sub_category': [f"{cat}_SubCat" for cat in prod_categories],
        'brand': np.random.choice(brands, size=num_products),
        'unit_cost': unit_costs
    })
    product_df.to_csv(os.path.join(output_dir, 'dim_product.csv'), index=False)
    print(f"  dim_product: {len(product_df)} rows")

    # 4. dim_customer (100,000 customers)
    num_customers = 100000
    countries = ['USA', 'Canada', 'UK', 'Germany', 'France', 'Australia']
    segments = ['Consumer', 'Corporate', 'Small Business', 'VIP', 'Enterprise']
    
    customer_df = pd.DataFrame({
        'customer_id': np.arange(1, num_customers + 1),
        'first_name': [f"UserFirst_{i}" for i in range(1, num_customers + 1)],
        'last_name': [f"UserLast_{i}" for i in range(1, num_customers + 1)],
        'email': [f"user_{i}@example.com" for i in range(1, num_customers + 1)],
        'country': np.random.choice(countries, size=num_customers, p=[0.5, 0.15, 0.15, 0.1, 0.05, 0.05]),
        'segment': np.random.choice(segments, size=num_customers, p=[0.6, 0.2, 0.1, 0.07, 0.03]),
        'signup_date': [dates[i].strftime('%Y-%m-%d') for i in np.random.randint(0, len(dates), size=num_customers)]
    })
    customer_df.to_csv(os.path.join(output_dir, 'dim_customer.csv'), index=False)
    print(f"  dim_customer: {len(customer_df)} rows")

    return date_df, store_df, product_df, customer_df

def generate_fact_sales(output_dir, num_rows, product_df):
    np.random.seed(SEED + 10)
    print(f"Generating fact_sales ({num_rows:,} rows) in {output_dir}...")

    # Zipf distribution for realistic product & customer popularity skew
    num_products = len(product_df)
    num_customers = 100000
    num_stores = 1000
    num_dates = 1095

    start_date = datetime(2023, 1, 1)
    dates = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(num_dates)]

    # Batch generation for high throughput & low memory footprint
    batch_size = 2_000_000
    fact_file = os.path.join(output_dir, 'fact_sales.csv')
    
    if os.path.exists(fact_file):
        os.remove(fact_file)

    written_rows = 0
    sale_id_counter = 1

    # Pre-extract product costs array for fast vector lookup
    product_costs = product_df['unit_cost'].values

    while written_rows < num_rows:
        current_batch_size = min(batch_size, num_rows - written_rows)
        
        # Power-law / Zipf skewed sampling for products and customers
        prod_idx = np.random.zipf(1.5, size=current_batch_size) % num_products
        cust_idx = np.random.zipf(1.4, size=current_batch_size) % num_customers
        
        product_ids = prod_idx + 1
        customer_ids = cust_idx + 1
        store_ids = np.random.randint(1, num_stores + 1, size=current_batch_size)
        date_indices = np.random.randint(0, num_dates, size=current_batch_size)
        date_ids = [dates[idx] for idx in date_indices]

        quantities = np.random.randint(1, 15, size=current_batch_size)
        
        # Unit price derived from unit_cost with margin multiplier
        margin_multipliers = np.random.uniform(1.15, 1.80, size=current_batch_size)
        unit_prices = np.round(product_costs[prod_idx] * margin_multipliers, 2)
        
        discounts = np.random.choice([0.0, 0.05, 0.10, 0.15, 0.20], size=current_batch_size, p=[0.5, 0.2, 0.15, 0.1, 0.05])
        
        raw_amount = quantities * unit_prices * (1.0 - discounts)
        tax_amounts = np.round(raw_amount * 0.08, 2)
        total_amounts = np.round(raw_amount + tax_amounts, 2)

        sale_ids = np.arange(sale_id_counter, sale_id_counter + current_batch_size)
        sale_id_counter += current_batch_size

        batch_df = pd.DataFrame({
            'sale_id': sale_ids,
            'customer_id': customer_ids,
            'product_id': product_ids,
            'store_id': store_ids,
            'date_id': date_ids,
            'quantity': quantities,
            'unit_price': unit_prices,
            'discount': discounts,
            'tax_amount': tax_amounts,
            'total_amount': total_amounts
        })

        header = not os.path.exists(fact_file)
        batch_df.to_csv(fact_file, mode='a', index=False, header=header)
        written_rows += current_batch_size
        print(f"  Progress: {written_rows:,} / {num_rows:,} rows written")

    print(f"Completed fact_sales generation ({num_rows:,} rows).")

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic star schema dataset.")
    parser.add_argument("--scale", type=str, choices=["10m", "1m", "both"], default="both", help="Data scale to generate")
    args = parser.parse_args()

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".data"))

    if args.scale in ["10m", "both"]:
        dir_10m = os.path.join(base_dir, "10m")
        _, _, prod_df, _ = generate_dimensions(dir_10m)
        generate_fact_sales(dir_10m, 10_000_000, prod_df)

    if args.scale in ["1m", "both"]:
        dir_1m = os.path.join(base_dir, "1m")
        _, _, prod_df, _ = generate_dimensions(dir_1m)
        generate_fact_sales(dir_1m, 1_000_000, prod_df)

    print("\nData generation complete!")

if __name__ == "__main__":
    main()
