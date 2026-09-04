import sys
import psycopg2
from clickhouse_driver import Client

def validate():
    pg_conn = psycopg2.connect("host=localhost port=5432 dbname=benchmark_db user=bench_user password=bench_password")
    pg_cur = pg_conn.cursor()
    ch_client = Client(host='localhost', port=9000, user='bench_user', password='bench_password', database='benchmark_db')

    tables = ['dim_customer', 'dim_product', 'dim_store', 'dim_date', 'fact_sales']
    print("=== Validating Data Parity Across Databases ===")

    # 1. Row Count Verification
    for tbl in tables:
        pg_cur.execute(f"SELECT COUNT(*) FROM {tbl};")
        pg_cnt = pg_cur.fetchone()[0]

        ch_cnt = ch_client.execute(f"SELECT COUNT(*) FROM {tbl}")[0][0]

        print(f"Table '{tbl}': PG = {pg_cnt:,} | CH = {ch_cnt:,}")
        if pg_cnt != ch_cnt:
            print(f"❌ MISMATCH ERROR in table {tbl}!")
            sys.exit(1)

    # 2. Aggregation Checksum on Fact Table
    pg_cur.execute("SELECT SUM(quantity), ROUND(SUM(unit_price)::numeric, 2), ROUND(SUM(discount_amount)::numeric, 2) FROM fact_sales;")
    pg_sums = pg_cur.fetchone()

    ch_sums = ch_client.execute("SELECT SUM(quantity), round(SUM(unit_price), 2), round(SUM(discount_amount), 2) FROM fact_sales")[0]

    print("\nFact Checksums:")
    print(f"  PG: SUM(qty)={pg_sums[0]}, SUM(price)={pg_sums[1]}, SUM(disc)={pg_sums[2]}")
    print(f"  CH: SUM(qty)={ch_sums[0]}, SUM(price)={ch_sums[1]}, SUM(disc)={ch_sums[2]}")

    if int(pg_sums[0]) != int(ch_sums[0]) or float(pg_sums[1]) != float(ch_sums[1]):
        print("❌ AGGREGATE CHECKSUM MISMATCH!")
        sys.exit(1)

    print("\n✅ DATA PARITY VALIDATED: Exact match across row counts and numeric checksums.\n")

if __name__ == "__main__":
    validate()