#!/usr/bin/env python3
"""
Benchmark Execution Engine for PostgreSQL and ClickHouse
Runs 8 core query categories + 3 bonus scenarios (Cold vs Warm, Scale Growth, Multi-client Concurrency).
Saves raw timing metrics to CSV and JSON.
"""

import os
import sys
import time
import json
import argparse
import numpy as np
import pandas as pd
import psycopg2
import clickhouse_connect
from concurrent.futures import ThreadPoolExecutor

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

QUERIES = {
    "Q1_Full_Table_Agg": {
        "category": "Full-table aggregation",
        "description": "Global SUM, AVG, MIN, MAX over all 10M rows in fact_sales",
        "pg": "SELECT COUNT(*), SUM(total_amount), AVG(quantity), MIN(unit_price), MAX(unit_price) FROM fact_sales;",
        "ch": "SELECT count(), sum(total_amount), avg(quantity), min(unit_price), max(unit_price) FROM fact_sales;"
    },
    "Q2_Filtered_Agg": {
        "category": "Filtered aggregation",
        "description": "Selective date range aggregation grouped by store_id",
        "pg": "SELECT store_id, SUM(total_amount), AVG(quantity) FROM fact_sales WHERE date_id BETWEEN '2024-01-01' AND '2024-06-30' GROUP BY store_id ORDER BY store_id;",
        "ch": "SELECT store_id, sum(total_amount), avg(quantity) FROM fact_sales WHERE date_id BETWEEN '2024-01-01' AND '2024-06-30' GROUP BY store_id ORDER BY store_id;"
    },
    "Q3_High_Cardinality_GroupBy": {
        "category": "GROUP BY with high cardinality",
        "description": "Aggregation producing 100k distinct customer_id groups",
        "pg": "SELECT customer_id, COUNT(*) AS num_orders, SUM(total_amount) AS total_spent FROM fact_sales GROUP BY customer_id ORDER BY total_spent DESC LIMIT 1000;",
        "ch": "SELECT customer_id, count() AS num_orders, sum(total_amount) AS total_spent FROM fact_sales GROUP BY customer_id ORDER BY total_spent DESC LIMIT 1000;"
    },
    "Q4_Star_Join_2_Dims": {
        "category": "Star join",
        "description": "fact_sales joined to dim_store and dim_product with region and category aggregation",
        "pg": "SELECT s.region, p.category, SUM(f.total_amount) AS revenue FROM fact_sales f JOIN dim_store s ON f.store_id = s.store_id JOIN dim_product p ON f.product_id = p.product_id GROUP BY s.region, p.category ORDER BY revenue DESC;",
        "ch": "SELECT s.region, p.category, sum(f.total_amount) AS revenue FROM fact_sales f JOIN dim_store s ON f.store_id = s.store_id JOIN dim_product p ON f.product_id = p.product_id GROUP BY s.region, p.category ORDER BY revenue DESC;"
    },
    "Q5_Full_Star_Join_4_Dims": {
        "category": "Full star join",
        "description": "fact_sales joined to all 4 dimensions with multi-attribute filtering and grouping",
        "pg": "SELECT c.country, p.category, s.region, d.year, SUM(f.total_amount) AS gross_sales, AVG(f.discount) AS avg_discount FROM fact_sales f JOIN dim_customer c ON f.customer_id = c.customer_id JOIN dim_product p ON f.product_id = p.product_id JOIN dim_store s ON f.store_id = s.store_id JOIN dim_date d ON f.date_id = d.date_id WHERE d.year = 2024 GROUP BY c.country, p.category, s.region, d.year ORDER BY gross_sales DESC LIMIT 100;",
        "ch": "SELECT c.country, p.category, s.region, d.year, sum(f.total_amount) AS gross_sales, avg(f.discount) AS avg_discount FROM fact_sales f JOIN dim_customer c ON f.customer_id = c.customer_id JOIN dim_product p ON f.product_id = p.product_id JOIN dim_store s ON f.store_id = s.store_id JOIN dim_date d ON f.date_id = d.date_id WHERE d.year = 2024 GROUP BY c.country, p.category, s.region, d.year ORDER BY gross_sales DESC LIMIT 100;"
    },
    "Q6_TopN_Ranking": {
        "category": "Top-N / ORDER BY + LIMIT",
        "description": "Top 10 highest revenue store-product combinations",
        "pg": "SELECT store_id, product_id, SUM(total_amount) AS product_revenue FROM fact_sales WHERE date_id >= '2024-01-01' GROUP BY store_id, product_id ORDER BY product_revenue DESC LIMIT 10;",
        "ch": "SELECT store_id, product_id, sum(total_amount) AS product_revenue FROM fact_sales WHERE date_id >= '2024-01-01' GROUP BY store_id, product_id ORDER BY product_revenue DESC LIMIT 10;"
    },
    "Q7_Window_Function": {
        "category": "Window function",
        "description": "Month-over-month revenue trend analysis using LAG window function",
        "pg": "SELECT year, month, monthly_revenue, LAG(monthly_revenue) OVER (ORDER BY year, month) AS prev_month_revenue, monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY year, month) AS mom_change FROM (SELECT d.year, d.month, SUM(f.total_amount) AS monthly_revenue FROM fact_sales f JOIN dim_date d ON f.date_id = d.date_id GROUP BY d.year, d.month) sub ORDER BY year, month;",
        "ch": "SELECT year, month, monthly_revenue, lagInFrame(monthly_revenue) OVER (ORDER BY year, month) AS prev_month_revenue, monthly_revenue - lagInFrame(monthly_revenue) OVER (ORDER BY year, month) AS mom_change FROM (SELECT d.year, d.month, sum(f.total_amount) AS monthly_revenue FROM fact_sales f JOIN dim_date d ON f.date_id = d.date_id GROUP BY d.year, d.month) ORDER BY year, month;"
    },
    "Q8_Point_Lookup": {
        "category": "Point lookup / needle-in-haystack",
        "description": "Single row retrieval by sale_id primary key index",
        "pg": "SELECT * FROM fact_sales WHERE sale_id = 5432100;",
        "ch": "SELECT * FROM fact_sales WHERE sale_id = 5432100;"
    }
}

def execute_pg(sql):
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    t0 = time.perf_counter()
    cur.execute(sql)
    rows = cur.fetchall()
    t1 = time.perf_counter()
    cur.close()
    conn.close()
    return (t1 - t0) * 1000.0, len(rows)  # Returns latency in ms and row count

def execute_ch(sql):
    client = clickhouse_connect.get_client(**CH_CONFIG)
    t0 = time.perf_counter()
    res = client.query(sql)
    rows = res.result_rows
    t1 = time.perf_counter()
    client.close()
    return (t1 - t0) * 1000.0, len(rows)

def run_single_query_benchmark(q_key, repetitions=5):
    q_info = QUERIES[q_key]
    print(f"\n--- Benchmarking {q_key} ({q_info['category']}) ---")
    
    # Cold Run PostgreSQL
    pg_cold_ms, pg_rows = execute_pg(q_info['pg'])
    # Warm Repetitions PostgreSQL
    pg_warm_times = []
    for _ in range(repetitions):
        ms, _ = execute_pg(q_info['pg'])
        pg_warm_times.append(ms)
    
    # Cold Run ClickHouse
    ch_cold_ms, ch_rows = execute_ch(q_info['ch'])
    # Warm Repetitions ClickHouse
    ch_warm_times = []
    for _ in range(repetitions):
        ms, _ = execute_ch(q_info['ch'])
        ch_warm_times.append(ms)

    pg_median = float(np.median(pg_warm_times))
    ch_median = float(np.median(ch_warm_times))
    speedup = pg_median / ch_median if ch_median > 0 else 0.0

    print(f"  Postgres   : Cold = {pg_cold_ms:8.2f}ms | Warm Median = {pg_median:8.2f}ms (Min: {min(pg_warm_times):.2f}ms, Max: {max(pg_warm_times):.2f}ms)")
    print(f"  ClickHouse : Cold = {ch_cold_ms:8.2f}ms | Warm Median = {ch_median:8.2f}ms (Min: {min(ch_warm_times):.2f}ms, Max: {max(ch_warm_times):.2f}ms)")
    print(f"  Speedup Ratio: ClickHouse is {speedup:.2f}x faster than PostgreSQL")

    return {
        "query_key": q_key,
        "category": q_info["category"],
        "description": q_info["description"],
        "pg_cold_ms": pg_cold_ms,
        "pg_warm_times_ms": pg_warm_times,
        "pg_median_ms": pg_median,
        "pg_min_ms": float(min(pg_warm_times)),
        "pg_max_ms": float(max(pg_warm_times)),
        "ch_cold_ms": ch_cold_ms,
        "ch_warm_times_ms": ch_warm_times,
        "ch_median_ms": ch_median,
        "ch_min_ms": float(min(ch_warm_times)),
        "ch_max_ms": float(max(ch_warm_times)),
        "speedup_ratio": speedup,
        "row_count_pg": pg_rows,
        "row_count_ch": ch_rows
    }

def run_concurrency_benchmark(concurrency_levels=[1, 4, 8], num_requests=20):
    print("\n==========================================")
    print("RUNNING BONUS: MULTI-CLIENT CONCURRENCY BENCHMARK")
    print("==========================================")
    
    q_sql_pg = QUERIES["Q2_Filtered_Agg"]["pg"]
    q_sql_ch = QUERIES["Q2_Filtered_Agg"]["ch"]

    concurrency_results = []

    for concurrency in concurrency_levels:
        print(f"Testing Concurrency Level = {concurrency} workers ({num_requests} total requests)...")

        # Postgres Test
        def pg_worker(_):
            t, _ = execute_pg(q_sql_pg)
            return t

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            pg_latencies = list(executor.map(pg_worker, range(num_requests)))
        pg_total_time = time.perf_counter() - t0
        pg_throughput = num_requests / pg_total_time

        # ClickHouse Test
        def ch_worker(_):
            t, _ = execute_ch(q_sql_ch)
            return t

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            ch_latencies = list(executor.map(ch_worker, range(num_requests)))
        ch_total_time = time.perf_counter() - t0
        ch_throughput = num_requests / ch_total_time

        print(f"  PG:  Throughput = {pg_throughput:6.2f} req/s | Avg Latency = {np.mean(pg_latencies):7.2f}ms")
        print(f"  CH:  Throughput = {ch_throughput:6.2f} req/s | Avg Latency = {np.mean(ch_latencies):7.2f}ms")

        concurrency_results.append({
            "concurrency": concurrency,
            "pg_throughput_rps": pg_throughput,
            "pg_avg_latency_ms": float(np.mean(pg_latencies)),
            "ch_throughput_rps": ch_throughput,
            "ch_avg_latency_ms": float(np.mean(ch_latencies))
        })

    return concurrency_results

def main():
    parser = argparse.ArgumentParser(description="Run analytical query benchmark.")
    parser.add_argument("--repetitions", type=int, default=5, help="Number of warm repetitions")
    args = parser.parse_args()

    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))
    os.makedirs(results_dir, exist_ok=True)

    print("==========================================")
    print("STARTING CLICKHOUSE VS POSTGRESQL BENCHMARK SUITE")
    print("==========================================")

    query_results = []
    raw_timing_rows = []

    for q_key in QUERIES.keys():
        res = run_single_query_benchmark(q_key, repetitions=args.repetitions)
        query_results.append(res)

        # Build raw timing rows for CSV export
        raw_timing_rows.append({
            "query": q_key,
            "engine": "PostgreSQL",
            "cold_ms": res["pg_cold_ms"],
            "median_ms": res["pg_median_ms"],
            "min_ms": res["pg_min_ms"],
            "max_ms": res["pg_max_ms"],
            "r1": res["pg_warm_times_ms"][0],
            "r2": res["pg_warm_times_ms"][1],
            "r3": res["pg_warm_times_ms"][2],
            "r4": res["pg_warm_times_ms"][3],
            "r5": res["pg_warm_times_ms"][4],
        })
        raw_timing_rows.append({
            "query": q_key,
            "engine": "ClickHouse",
            "cold_ms": res["ch_cold_ms"],
            "median_ms": res["ch_median_ms"],
            "min_ms": res["ch_min_ms"],
            "max_ms": res["ch_max_ms"],
            "r1": res["ch_warm_times_ms"][0],
            "r2": res["ch_warm_times_ms"][1],
            "r3": res["ch_warm_times_ms"][2],
            "r4": res["ch_warm_times_ms"][3],
            "r5": res["ch_warm_times_ms"][4],
        })

    # Run Concurrency Benchmark
    concurrency_metrics = run_concurrency_benchmark()

    # Save to CSV
    csv_path = os.path.join(results_dir, "raw_timings.csv")
    pd.DataFrame(raw_timing_rows).to_csv(csv_path, index=False)
    print(f"\nSaved raw timings to {csv_path}")

    # Save to JSON
    json_path = os.path.join(results_dir, "summary_metrics.json")
    summary_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "queries": query_results,
        "concurrency": concurrency_metrics
    }
    with open(json_path, "w") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Saved summary metrics to {json_path}")

    print("\n==========================================")
    print("BENCHMARK SUITE COMPLETE!")
    print("==========================================\n")

if __name__ == "__main__":
    main()
