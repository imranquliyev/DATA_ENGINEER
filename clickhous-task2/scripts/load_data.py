import time
import subprocess
import psycopg2
from clickhouse_driver import Client

def load_postgres():
    print("Loading data into PostgreSQL...")
    conn = psycopg2.connect("host=localhost port=5432 dbname=benchmark_db user=bench_user password=bench_password")
    cur = conn.cursor()
    
    # Apply schema
    with open("sql/pg_schema.sql") as f:
        cur.execute(f.read())
    conn.commit()

    tables = ['dim_customer', 'dim_product', 'dim_store', 'dim_date', 'fact_sales']
    start_total = time.time()
    
    for tbl in tables:
        t0 = time.time()
        with open(f"data/{tbl}.csv", 'r') as f:
            cur.copy_expert(f"COPY {tbl} FROM STDIN WITH (FORMAT csv, HEADER true)", f)
        conn.commit()
        print(f"  [PG] Loaded {tbl} in {time.time() - t0:.2f}s")
    
    print(f"PostgreSQL Total Ingestion Time: {time.time() - start_total:.2f}s\n")
    cur.close()
    conn.close()

def load_clickhouse():
    print("Loading data into ClickHouse...")
    client = Client(host='localhost', port=9000, user='bench_user', password='bench_password', database='benchmark_db')
    
    # Apply schema
    with open("sql/ch_schema.sql") as f:
        statements = f.read().split(';')
        for stmt in statements:
            if stmt.strip():
                client.execute(stmt)

    tables = ['dim_customer', 'dim_product', 'dim_store', 'dim_date', 'fact_sales']
    start_total = time.time()

    # Stream CSVs directly into clickhouse-client inside the container
    for tbl in tables:
        t0 = time.time()
        cmd = [
            "docker", "exec", "-i", "benchmark_clickhouse",
            "clickhouse-client",
            "--user", "bench_user",
            "--password", "bench_password",
            "--database", "benchmark_db",
            "--query", f"INSERT INTO {tbl} FORMAT CSVWithNames"
        ]
        with open(f"data/{tbl}.csv", "rb") as f:
            subprocess.run(cmd, stdin=f, check=True)
            
        print(f"  [CH] Loaded {tbl} in {time.time() - t0:.2f}s")

    print(f"ClickHouse Total Ingestion Time: {time.time() - start_total:.2f}s\n")

if __name__ == "__main__":
    load_postgres()
    load_clickhouse()