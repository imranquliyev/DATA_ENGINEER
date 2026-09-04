import time
import json
import numpy as np
import psycopg2
from clickhouse_driver import Client

QUERIES = {
    "Q1_Full_Aggregation": {
        "category": "Full-table Aggregation",
        "pg": """
            SELECT 
                SUM(quantity) AS total_qty,
                SUM(quantity * unit_price - discount_amount) AS net_revenue,
                AVG(discount_amount) AS avg_discount
            FROM fact_sales;
        """,
        "ch": """
            SELECT 
                SUM(quantity) AS total_qty,
                SUM(quantity * unit_price - discount_amount) AS net_revenue,
                AVG(discount_amount) AS avg_discount
            FROM fact_sales;
        """
    },
    "Q2_Filtered_Aggregation": {
        "category": "Filtered Aggregation",
        "pg": """
            SELECT 
                s.region,
                SUM(f.quantity * f.unit_price - f.discount_amount) AS net_sales
            FROM fact_sales f
            JOIN dim_store s ON f.store_id = s.store_id
            WHERE f.date_key BETWEEN 20241001 AND 20241231
              AND s.region = 'North'
            GROUP BY s.region;
        """,
        "ch": """
            SELECT 
                s.region,
                SUM(f.quantity * f.unit_price - f.discount_amount) AS net_sales
            FROM fact_sales f
            JOIN dim_store s ON f.store_id = s.store_id
            WHERE f.date_key BETWEEN 20241001 AND 20241231
              AND s.region = 'North'
            GROUP BY s.region;
        """
    },
    "Q3_High_Cardinality_GroupBy": {
        "category": "GROUP BY High Cardinality",
        "pg": """
            SELECT 
                customer_id,
                COUNT(order_id) AS total_orders,
                SUM(quantity * unit_price - discount_amount) AS total_spent
            FROM fact_sales
            GROUP BY customer_id
            ORDER BY total_spent DESC
            LIMIT 100;
        """,
        "ch": """
            SELECT 
                customer_id,
                COUNT(order_id) AS total_orders,
                SUM(quantity * unit_price - discount_amount) AS total_spent
            FROM fact_sales
            GROUP BY customer_id
            ORDER BY total_spent DESC
            LIMIT 100;
        """
    },
    "Q4_Star_Join_2_Dims": {
        "category": "Star Join",
        "pg": """
            SELECT 
                p.category,
                d.year,
                SUM(f.quantity * f.unit_price) AS gross_sales
            FROM fact_sales f
            JOIN dim_product p ON f.product_id = p.product_id
            JOIN dim_date d ON f.date_key = d.date_key
            GROUP BY p.category, d.year
            ORDER BY p.category, d.year;
        """,
        "ch": """
            SELECT 
                p.category,
                d.year,
                SUM(f.quantity * f.unit_price) AS gross_sales
            FROM fact_sales f
            JOIN dim_product p ON f.product_id = p.product_id
            JOIN dim_date d ON f.date_key = d.date_key
            GROUP BY p.category, d.year
            ORDER BY p.category, d.year;
        """
    },
    "Q5_Full_Star_Join": {
        "category": "Full Star Join",
        "pg": """
            SELECT 
                st.region,
                p.category,
                c.segment,
                d.year,
                SUM(f.quantity * f.unit_price - f.discount_amount) AS net_revenue
            FROM fact_sales f
            JOIN dim_customer c ON f.customer_id = c.customer_id
            JOIN dim_product p ON f.product_id = p.product_id
            JOIN dim_store st ON f.store_id = st.store_id
            JOIN dim_date d ON f.date_key = d.date_key
            GROUP BY st.region, p.category, c.segment, d.year;
        """,
        "ch": """
            SELECT 
                st.region,
                p.category,
                c.segment,
                d.year,
                SUM(f.quantity * f.unit_price - f.discount_amount) AS net_revenue
            FROM fact_sales f
            JOIN dim_customer c ON f.customer_id = c.customer_id
            JOIN dim_product p ON f.product_id = p.product_id
            JOIN dim_store st ON f.store_id = st.store_id
            JOIN dim_date d ON f.date_key = d.date_key
            GROUP BY st.region, p.category, c.segment, d.year;
        """
    },
    "Q6_Top_N_Limit": {
        "category": "Top-N / ORDER BY + LIMIT",
        "pg": """
            SELECT 
                p.product_name,
                SUM(f.quantity * f.unit_price - f.discount_amount) AS total_revenue
            FROM fact_sales f
            JOIN dim_product p ON f.product_id = p.product_id
            WHERE f.date_key BETWEEN 20240101 AND 20241231
            GROUP BY p.product_name
            ORDER BY total_revenue DESC
            LIMIT 10;
        """,
        "ch": """
            SELECT 
                p.product_name,
                SUM(f.quantity * f.unit_price - f.discount_amount) AS total_revenue
            FROM fact_sales f
            JOIN dim_product p ON f.product_id = p.product_id
            WHERE f.date_key BETWEEN 20240101 AND 20241231
            GROUP BY p.product_name
            ORDER BY total_revenue DESC
            LIMIT 10;
        """
    },
    "Q7_Window_Function": {
        "category": "Window Function",
        "pg": """
            WITH monthly_sales AS (
                SELECT 
                    store_id,
                    date_key / 100 AS year_month,
                    SUM(quantity * unit_price - discount_amount) AS monthly_rev
                FROM fact_sales
                GROUP BY store_id, date_key / 100
            )
            SELECT 
                store_id,
                year_month,
                monthly_rev,
                SUM(monthly_rev) OVER (PARTITION BY store_id ORDER BY year_month) AS running_total
            FROM monthly_sales;
        """,
        "ch": """
            WITH monthly_sales AS (
                SELECT 
                    store_id,
                    intDiv(date_key, 100) AS year_month,
                    SUM(quantity * unit_price - discount_amount) AS monthly_rev
                FROM fact_sales
                GROUP BY store_id, year_month
            )
            SELECT 
                store_id,
                year_month,
                monthly_rev,
                SUM(monthly_rev) OVER (PARTITION BY store_id ORDER BY year_month) AS running_total
            FROM monthly_sales;
        """
    },
    "Q8_Point_Lookup": {
        "category": "Point Lookup",
        "pg": """
            SELECT * FROM fact_sales 
            WHERE order_id IN (500000, 1500000, 4500000, 7500000, 9500000);
        """,
        "ch": """
            SELECT * FROM fact_sales 
            WHERE order_id IN (500000, 1500000, 4500000, 7500000, 9500000);
        """
    }
}

def run_benchmark(repetitions=5, warmup=1):
    pg_conn = psycopg2.connect("host=localhost port=5432 dbname=benchmark_db user=bench_user password=bench_password")
    pg_cur = pg_conn.cursor()
    ch_client = Client(host='localhost', port=9000, user='bench_user', password='bench_password', database='benchmark_db')

    results = {}

    for q_name, q_info in QUERIES.items():
        print(f"Running Benchmark: {q_name} ({q_info['category']})...")
        results[q_name] = {"category": q_info["category"], "pg": [], "ch": []}

        # --- PostgreSQL ---
        # Warmup
        for _ in range(warmup):
            pg_cur.execute(q_info["pg"])
            pg_cur.fetchall()
        
        # Repetitions
        for _ in range(repetitions):
            t0 = time.perf_counter()
            pg_cur.execute(q_info["pg"])
            pg_cur.fetchall()
            t1 = time.perf_counter()
            results[q_name]["pg"].append((t1 - t0) * 1000.0)  # ms

        # --- ClickHouse ---
        # Warmup
        for _ in range(warmup):
            ch_client.execute(q_info["ch"])
        
        # Repetitions
        for _ in range(repetitions):
            t0 = time.perf_counter()
            ch_client.execute(q_info["ch"])
            t1 = time.perf_counter()
            results[q_name]["ch"].append((t1 - t0) * 1000.0)  # ms

    # Save summary
    summary = {}
    for q_name, data in results.items():
        pg_med = float(np.median(data["pg"]))
        ch_med = float(np.median(data["ch"]))
        ratio = pg_med / ch_med if ch_med > 0 else 0
        summary[q_name] = {
            "category": data["category"],
            "pg_median_ms": round(pg_med, 2),
            "pg_min_ms": round(float(np.min(data["pg"])), 2),
            "pg_max_ms": round(float(np.max(data["pg"])), 2),
            "ch_median_ms": round(ch_med, 2),
            "ch_min_ms": round(float(np.min(data["ch"])), 2),
            "ch_max_ms": round(float(np.max(data["ch"])), 2),
            "speedup_ratio": round(ratio, 2)
        }

    with open("benchmark_results.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\nBenchmark Execution Complete. Results written to benchmark_results.json.")

if __name__ == "__main__":
    run_benchmark()