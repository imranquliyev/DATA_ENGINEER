#!/usr/bin/env python3
"""
Data Parity Validator across PostgreSQL and ClickHouse
Validates row counts, aggregate checksums, and distinct value counts.
Fails loudly (exit code 1) if data parity is violated.
"""

import sys
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

def query_pg(sql):
    conn = psycopg2.connect(**PG_CONFIG)
    with conn.cursor() as cur:
        cur.execute(sql)
        res = cur.fetchall()
    conn.close()
    return res

def query_ch(sql):
    client = clickhouse_connect.get_client(**CH_CONFIG)
    res = client.query(sql).result_rows
    client.close()
    return res

def check_value(metric_name, pg_val, ch_val, tolerance=1e-2):
    try:
        pg_num = float(pg_val)
        ch_num = float(ch_val)
        diff = abs(pg_num - ch_num)
        if diff <= tolerance:
            print(f"  [PASS] {metric_name:35s}: PG = {pg_num:15.2f} | CH = {ch_num:15.2f}")
            return True
        else:
            print(f"  [FAIL] {metric_name:35s}: PG = {pg_num:15.2f} | CH = {ch_num:15.2f} (Diff: {diff:.4f})")
            return False
    except (ValueError, TypeError):
        if str(pg_val) == str(ch_val):
            print(f"  [PASS] {metric_name:35s}: PG = {pg_val} | CH = {ch_val}")
            return True
        else:
            print(f"  [FAIL] {metric_name:35s}: PG = {pg_val} | CH = {ch_val}")
            return False

def main():
    print("==========================================")
    print("RUNNING DATA PARITY VALIDATION")
    print("==========================================")

    all_passed = True

    validations = [
        # (Table/Metric Name, PG SQL, CH SQL)
        ("fact_sales Row Count", "SELECT COUNT(*) FROM fact_sales", "SELECT count() FROM fact_sales"),
        ("fact_sales Total Revenue SUM", "SELECT SUM(total_amount) FROM fact_sales", "SELECT sum(total_amount) FROM fact_sales"),
        ("fact_sales Quantity AVG", "SELECT AVG(quantity) FROM fact_sales", "SELECT avg(quantity) FROM fact_sales"),
        ("fact_sales Distinct Products", "SELECT COUNT(DISTINCT product_id) FROM fact_sales", "SELECT count(DISTINCT product_id) FROM fact_sales"),
        ("fact_sales Distinct Customers", "SELECT COUNT(DISTINCT customer_id) FROM fact_sales", "SELECT count(DISTINCT customer_id) FROM fact_sales"),
        ("dim_customer Row Count", "SELECT COUNT(*) FROM dim_customer", "SELECT count() FROM dim_customer"),
        ("dim_product Row Count", "SELECT COUNT(*) FROM dim_product", "SELECT count() FROM dim_product"),
        ("dim_product SUM(unit_cost)", "SELECT SUM(unit_cost) FROM dim_product", "SELECT sum(unit_cost) FROM dim_product"),
        ("dim_store Row Count", "SELECT COUNT(*) FROM dim_store", "SELECT count() FROM dim_store"),
        ("dim_date Row Count", "SELECT COUNT(*) FROM dim_date", "SELECT count() FROM dim_date"),
    ]

    for label, pg_sql, ch_sql in validations:
        pg_res = query_pg(pg_sql)[0][0]
        ch_res = query_ch(ch_sql)[0][0]
        passed = check_value(label, pg_res, ch_res)
        if not passed:
            all_passed = False

    print("==========================================")
    if all_passed:
        print("VALIDATION SUCCESSFUL: DATA PARITY VERIFIED ACROSS BOTH DATABASES.")
        print("==========================================\n")
        sys.exit(0)
    else:
        print("VALIDATION FAILED: DISCREPANCY DETECTED BETWEEN DATABASES!")
        print("==========================================\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
