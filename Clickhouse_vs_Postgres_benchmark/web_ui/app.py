#!/usr/bin/env python3
"""
Interactive Web Dashboard & Query Explorer for ClickHouse vs. PostgreSQL Benchmark
Provides REST APIs for live query execution, data browsing, and latency comparison.
"""

import os
import sys
import time
import json
from flask import Flask, jsonify, request, render_template
import psycopg2
from psycopg2.extras import RealDictCursor
import clickhouse_connect

app = Flask(__name__)

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

PRESET_QUERIES = {
    "Q1": {
        "title": "Q1: Full-Table Aggregation",
        "category": "Full-table aggregation",
        "description": "Global SUM, AVG, MIN, MAX over all 10M rows in fact_sales",
        "pg": "SELECT COUNT(*), SUM(total_amount), AVG(quantity), MIN(unit_price), MAX(unit_price) FROM fact_sales;",
        "ch": "SELECT count(), sum(total_amount), avg(quantity), min(unit_price), max(unit_price) FROM fact_sales;"
    },
    "Q2": {
        "title": "Q2: Filtered Aggregation",
        "category": "Filtered aggregation",
        "description": "Selective date range aggregation grouped by store_id",
        "pg": "SELECT store_id, SUM(total_amount) AS revenue, AVG(quantity) AS avg_qty FROM fact_sales WHERE date_id BETWEEN '2024-01-01' AND '2024-06-30' GROUP BY store_id ORDER BY store_id LIMIT 50;",
        "ch": "SELECT store_id, sum(total_amount) AS revenue, avg(quantity) AS avg_qty FROM fact_sales WHERE date_id BETWEEN '2024-01-01' AND '2024-06-30' GROUP BY store_id ORDER BY store_id LIMIT 50;"
    },
    "Q3": {
        "title": "Q3: High-Cardinality GROUP BY",
        "category": "GROUP BY with high cardinality",
        "description": "Aggregation producing 100k distinct customer_id groups",
        "pg": "SELECT customer_id, COUNT(*) AS num_orders, SUM(total_amount) AS total_spent FROM fact_sales GROUP BY customer_id ORDER BY total_spent DESC LIMIT 50;",
        "ch": "SELECT customer_id, count() AS num_orders, sum(total_amount) AS total_spent FROM fact_sales GROUP BY customer_id ORDER BY total_spent DESC LIMIT 50;"
    },
    "Q4": {
        "title": "Q4: Star Join (2 Dimensions)",
        "category": "Star join",
        "description": "fact_sales joined to dim_store and dim_product with region and category aggregation",
        "pg": "SELECT s.region, p.category, SUM(f.total_amount) AS revenue FROM fact_sales f JOIN dim_store s ON f.store_id = s.store_id JOIN dim_product p ON f.product_id = p.product_id GROUP BY s.region, p.category ORDER BY revenue DESC LIMIT 50;",
        "ch": "SELECT s.region, p.category, sum(f.total_amount) AS revenue FROM fact_sales f JOIN dim_store s ON f.store_id = s.store_id JOIN dim_product p ON f.product_id = p.product_id GROUP BY s.region, p.category ORDER BY revenue DESC LIMIT 50;"
    },
    "Q5": {
        "title": "Q5: Full Star Join (All 4 Dimensions)",
        "category": "Full star join",
        "description": "fact_sales joined to all 4 dimensions with multi-dimensional slicing",
        "pg": "SELECT c.country, p.category, s.region, d.year, SUM(f.total_amount) AS gross_sales, AVG(f.discount) AS avg_discount FROM fact_sales f JOIN dim_customer c ON f.customer_id = c.customer_id JOIN dim_product p ON f.product_id = p.product_id JOIN dim_store s ON f.store_id = s.store_id JOIN dim_date d ON f.date_id = d.date_id WHERE d.year = 2024 GROUP BY c.country, p.category, s.region, d.year ORDER BY gross_sales DESC LIMIT 50;",
        "ch": "SELECT c.country, p.category, s.region, d.year, sum(f.total_amount) AS gross_sales, avg(f.discount) AS avg_discount FROM fact_sales f JOIN dim_customer c ON f.customer_id = c.customer_id JOIN dim_product p ON f.product_id = p.product_id JOIN dim_store s ON f.store_id = s.store_id JOIN dim_date d ON f.date_id = d.date_id WHERE d.year = 2024 GROUP BY c.country, p.category, s.region, d.year ORDER BY gross_sales DESC LIMIT 50;"
    },
    "Q6": {
        "title": "Q6: Top-N Ranking",
        "category": "Top-N / ORDER BY + LIMIT",
        "description": "Top 10 highest revenue store-product combinations",
        "pg": "SELECT store_id, product_id, SUM(total_amount) AS product_revenue FROM fact_sales WHERE date_id >= '2024-01-01' GROUP BY store_id, product_id ORDER BY product_revenue DESC LIMIT 10;",
        "ch": "SELECT store_id, product_id, sum(total_amount) AS product_revenue FROM fact_sales WHERE date_id >= '2024-01-01' GROUP BY store_id, product_id ORDER BY product_revenue DESC LIMIT 10;"
    },
    "Q7": {
        "title": "Q7: Window Function Trend",
        "category": "Window function",
        "description": "Month-over-month revenue trend using LAG() window function",
        "pg": "SELECT year, month, monthly_revenue, LAG(monthly_revenue) OVER (ORDER BY year, month) AS prev_month_revenue FROM (SELECT d.year, d.month, SUM(f.total_amount) AS monthly_revenue FROM fact_sales f JOIN dim_date d ON f.date_id = d.date_id GROUP BY d.year, d.month) sub ORDER BY year, month;",
        "ch": "SELECT year, month, monthly_revenue, lagInFrame(monthly_revenue) OVER (ORDER BY year, month) AS prev_month_revenue FROM (SELECT d.year, d.month, sum(f.total_amount) AS monthly_revenue FROM fact_sales f JOIN dim_date d ON f.date_id = d.date_id GROUP BY d.year, d.month) ORDER BY year, month;"
    },
    "Q8": {
        "title": "Q8: Point Lookup (Needle in Haystack)",
        "category": "Point lookup",
        "description": "Single row retrieval by sale_id primary key index",
        "pg": "SELECT * FROM fact_sales WHERE sale_id = 5432100;",
        "ch": "SELECT * FROM fact_sales WHERE sale_id = 5432100;"
    }
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    status = {"postgres": False, "clickhouse": False, "pg_rows": 0, "ch_rows": 0}
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM fact_sales;")
        status["pg_rows"] = cur.fetchone()[0]
        status["postgres"] = True
        conn.close()
    except Exception as e:
        status["pg_error"] = str(e)

    try:
        client = clickhouse_connect.get_client(**CH_CONFIG)
        res = client.query("SELECT count() FROM fact_sales")
        status["ch_rows"] = res.result_rows[0][0]
        status["clickhouse"] = True
        client.close()
    except Exception as e:
        status["ch_error"] = str(e)

    return jsonify(status)

@app.route('/api/presets', methods=['GET'])
def get_presets():
    return jsonify(PRESET_QUERIES)

@app.route('/api/data/<table_name>', methods=['GET'])
def browse_table(table_name):
    allowed_tables = ['fact_sales', 'dim_customer', 'dim_product', 'dim_store', 'dim_date']
    if table_name not in allowed_tables:
        return jsonify({"error": "Invalid table"}), 400

    db_type = request.args.get('db', 'postgres')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    offset = (page - 1) * limit

    t0 = time.perf_counter()
    rows = []
    columns = []

    if db_type == 'postgres':
        try:
            conn = psycopg2.connect(**PG_CONFIG)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(f"SELECT * FROM {table_name} ORDER BY 1 LIMIT %s OFFSET %s;", (limit, offset))
            dict_rows = cur.fetchall()
            columns = list(dict_rows[0].keys()) if dict_rows else []
            rows = [list(r.values()) for r in dict_rows]
            conn.close()
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        try:
            client = clickhouse_connect.get_client(**CH_CONFIG)
            res = client.query(f"SELECT * FROM {table_name} LIMIT {limit} OFFSET {offset}")
            columns = res.column_names
            rows = res.result_rows
            client.close()
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # Convert non-serializable objects (like datetime.date) to str
    clean_rows = []
    for r in rows:
        clean_rows.append([str(v) if not isinstance(v, (int, float, type(None))) else v for v in r])

    return jsonify({
        "table": table_name,
        "db": db_type,
        "page": page,
        "limit": limit,
        "latency_ms": round(elapsed_ms, 2),
        "columns": columns,
        "rows": clean_rows
    })

@app.route('/api/query/run', methods=['POST'])
def run_query():
    body = request.get_json() or {}
    pg_sql = body.get('pg_sql')
    ch_sql = body.get('ch_sql')
    preset_key = body.get('preset_key')

    if preset_key and preset_key in PRESET_QUERIES:
        pg_sql = PRESET_QUERIES[preset_key]['pg']
        ch_sql = PRESET_QUERIES[preset_key]['ch']

    if not pg_sql or not ch_sql:
        return jsonify({"error": "Missing pg_sql or ch_sql"}), 400

    results = {}

    # Run Postgres Query
    try:
        t0 = time.perf_counter()
        conn = psycopg2.connect(**PG_CONFIG)
        cur = conn.cursor()
        cur.execute(pg_sql)
        pg_rows = cur.fetchall()
        pg_cols = [desc[0] for desc in cur.description] if cur.description else []
        t1 = time.perf_counter()
        conn.close()
        
        pg_clean = []
        for r in pg_rows[:50]:
            pg_clean.append([str(v) if not isinstance(v, (int, float, type(None))) else v for v in r])

        results["postgres"] = {
            "latency_ms": round((t1 - t0) * 1000.0, 2),
            "columns": pg_cols,
            "rows": pg_clean,
            "total_rows": len(pg_rows)
        }
    except Exception as e:
        results["postgres"] = {"error": str(e)}

    # Run ClickHouse Query
    try:
        t0 = time.perf_counter()
        client = clickhouse_connect.get_client(**CH_CONFIG)
        ch_res = client.query(ch_sql)
        t1 = time.perf_counter()
        client.close()

        ch_clean = []
        for r in ch_res.result_rows[:50]:
            ch_clean.append([str(v) if not isinstance(v, (int, float, type(None))) else v for v in r])

        results["clickhouse"] = {
            "latency_ms": round((t1 - t0) * 1000.0, 2),
            "columns": ch_res.column_names,
            "rows": ch_clean,
            "total_rows": len(ch_res.result_rows)
        }
    except Exception as e:
        results["clickhouse"] = {"error": str(e)}

    if "latency_ms" in results["postgres"] and "latency_ms" in results["clickhouse"]:
        pg_lat = results["postgres"]["latency_ms"]
        ch_lat = results["clickhouse"]["latency_ms"]
        results["speedup_ratio"] = round(pg_lat / ch_lat, 2) if ch_lat > 0 else 0.0

    return jsonify(results)

@app.route('/api/benchmark/summary', methods=['GET'])
def get_benchmark_summary():
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))
    json_path = os.path.join(results_dir, "summary_metrics.json")
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            return jsonify(json.load(f))
    return jsonify({"error": "Summary metrics not found"}), 404

if __name__ == '__main__':
    print("Starting Interactive Benchmark Web UI on http://127.0.0.1:5050...")
    app.run(host='0.0.0.0', port=5050, debug=False)
