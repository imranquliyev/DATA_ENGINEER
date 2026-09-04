#!/usr/bin/env python3
"""
Data Loader for PostgreSQL and ClickHouse
Applies schema DDL and bulk loads generated CSV files into both databases.
Measures and reports ingestion performance.
"""

import os
import sys
import time
import argparse
import psycopg2
import clickhouse_connect

PG_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "dbname": "benchmark_db",
    "user": "postgres",
    "password": "postgres"
}

CH_CONFIG = {
    "host": "127.0.0.1",
    "port": 8123,
    "username": "default",
    "password": "clickhouse",
    "database": "benchmark_db"
}

def get_pg_connection():
    return psycopg2.connect(**PG_CONFIG)

def get_ch_client():
    return clickhouse_connect.get_client(**CH_CONFIG)

def setup_schemas(schema_dir):
    print("Setting up schemas in both databases...")
    
    # Setup PostgreSQL Schema
    pg_schema_path = os.path.join(schema_dir, 'postgres_schema.sql')
    with open(pg_schema_path, 'r') as f:
        pg_sql = f.read()
    
    conn = get_pg_connection()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(pg_sql)
    conn.close()
    print("  PostgreSQL schema applied successfully.")

    # Setup ClickHouse Schema
    ch_schema_path = os.path.join(schema_dir, 'clickhouse_schema.sql')
    with open(ch_schema_path, 'r') as f:
        ch_sql = f.read()
    
    client = get_ch_client()
    for statement in ch_sql.split(';'):
        stmt = statement.strip()
        if stmt:
            client.command(stmt)
    client.close()
    print("  ClickHouse schema applied successfully.")

def load_postgres(data_dir):
    print(f"\nLoading data into PostgreSQL from {data_dir}...")
    tables = ['dim_date', 'dim_store', 'dim_product', 'dim_customer', 'fact_sales']
    
    conn = get_pg_connection()
    conn.autocommit = False
    cur = conn.cursor()

    load_times = {}
    total_start = time.time()

    for table in tables:
        file_path = os.path.join(data_dir, f"{table}.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Data file not found: {file_path}")
        
        t0 = time.time()
        print(f"  Loading {table}...")
        with open(file_path, 'r') as f:
            cur.copy_expert(f"COPY {table} FROM STDIN WITH (FORMAT csv, HEADER true)", f)
        conn.commit()
        t1 = time.time()
        elapsed = t1 - t0
        load_times[table] = elapsed
        print(f"    Loaded {table} in {elapsed:.2f} seconds.")

    total_elapsed = time.time() - total_start
    
    print("  Creating PostgreSQL B-Tree indexes...")
    idx_t0 = time.time()
    cur.execute("CREATE INDEX idx_fact_customer_id ON fact_sales(customer_id);")
    cur.execute("CREATE INDEX idx_fact_product_id ON fact_sales(product_id);")
    cur.execute("CREATE INDEX idx_fact_store_id ON fact_sales(store_id);")
    cur.execute("CREATE INDEX idx_fact_date_id ON fact_sales(date_id);")
    conn.commit()
    idx_elapsed = time.time() - idx_t0
    print(f"    Created indexes in {idx_elapsed:.2f} seconds.")

    cur.close()
    conn.close()
    print(f"PostgreSQL total load & indexing time: {total_elapsed + idx_elapsed:.2f} seconds.")
    return total_elapsed + idx_elapsed, load_times

def load_clickhouse(data_dir):
    print(f"\nLoading data into ClickHouse from {data_dir}...")
    tables = ['dim_date', 'dim_store', 'dim_product', 'dim_customer', 'fact_sales']
    
    client = get_ch_client()
    load_times = {}
    total_start = time.time()

    for table in tables:
        file_path = os.path.join(data_dir, f"{table}.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Data file not found: {file_path}")
        
        t0 = time.time()
        print(f"  Loading {table}...")
        
        # Stream insertion using raw CSV stream / clickhouse_connect raw_insert
        with open(file_path, 'rb') as f:
            client.raw_insert(table=table, fmt='CSVWithNames', insert_block=f)
        
        t1 = time.time()
        elapsed = t1 - t0
        load_times[table] = elapsed
        print(f"    Loaded {table} in {elapsed:.2f} seconds.")

    total_elapsed = time.time() - total_start
    client.close()
    print(f"ClickHouse total load time: {total_elapsed:.2f} seconds.")
    return total_elapsed, load_times

def main():
    parser = argparse.ArgumentParser(description="Load data into PostgreSQL and ClickHouse.")
    parser.add_argument("--scale", type=str, choices=["10m", "1m"], default="10m", help="Data scale to load")
    args = parser.parse_args()

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_dir = os.path.join(base_dir, ".data", args.scale)
    schema_dir = os.path.join(base_dir, "schema")

    if not os.path.exists(data_dir):
        print(f"Data directory {data_dir} does not exist. Run `make generate` first.")
        sys.exit(1)

    setup_schemas(schema_dir)
    pg_total, pg_times = load_postgres(data_dir)
    ch_total, ch_times = load_clickhouse(data_dir)

    print("\n==========================================")
    print("INGESTION PERFORMANCE SUMMARY")
    print("==========================================")
    print(f"PostgreSQL Total Load Time: {pg_total:.2f}s")
    print(f"ClickHouse Total Load Time: {ch_total:.2f}s")
    if ch_total > 0:
        ratio = pg_total / ch_total
        print(f"Ingestion Speedup: ClickHouse is {ratio:.2f}x faster than PostgreSQL")
    print("==========================================\n")

if __name__ == "__main__":
    main()
