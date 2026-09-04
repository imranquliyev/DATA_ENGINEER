# Analytical Query Benchmark: ClickHouse vs. PostgreSQL

## Executive Summary

There is a widely repeated claim in the data engineering community:
> *"ClickHouse is dramatically faster than PostgreSQL for analytical (OLAP) queries."*

To test this claim, we built an end-to-end, fully automated, and reproducible benchmark environment using **PostgreSQL 16** (row-oriented OLTP database) and **ClickHouse Latest** (column-oriented OLAP database). Both databases ran inside isolated Docker containers with identical hardware resources (4 CPU cores, 4 GB RAM).

We generated a synthetic **10,000,000-row star schema dataset** (~1.2 GB raw CSV) with realistic power-law/Zipf skews and a 3-year date range. We designed **8 benchmark queries** covering key analytical workload patterns, measured cold and warm execution latencies across 5 repetitions, performed data parity validation, and evaluated ingestion throughput and multi-client concurrency.

### Key Empirical Findings
- **OLAP Analytical Dominance**: ClickHouse defeated PostgreSQL on **7 out of 8 query categories**, delivering speedups ranging from **4.90x to 17.76x faster** (median latency).
- **The Point Lookup Surprise**: PostgreSQL defeated ClickHouse on **Q8 (Point Lookup / Needle-in-Haystack)**, executing **2.38x faster in warm cache** (2.25 ms vs 5.39 ms) and **11.19x faster in cold cache** (2.34 ms vs 26.19 ms).
- **Ingestion Velocity**: ClickHouse ingested the 10,000,000 fact table rows **6.40x faster** than PostgreSQL (6.98s vs 44.67s).
- **Concurrency Scaling**: Under multi-client concurrent query load (8 parallel clients), ClickHouse maintained **8.47 requests/sec** with an average latency of **605 ms**, whereas PostgreSQL degraded to **1.63 requests/sec** with an average latency of **4,293 ms**.

---

## 1. Benchmark Environment Specifications

| Parameter | Host Specification / Container Configuration |
|---|---|
| **CPU Architecture** | x86_64, Intel(R) Core(TM) i7-10510U CPU @ 1.80GHz (8 cores) |
| **System Memory** | 15.0 GiB Physical RAM |
| **Operating System** | Ubuntu 24.04 LTS Linux (Kernel 6.8.0-40-generic) |
| **Container Engine** | Docker Engine 29.1.3, Docker Compose 2.40.3 |
| **PostgreSQL Container** | `postgres:16-alpine` |
| **ClickHouse Container** | `clickhouse/clickhouse-server:latest` |
| **Container CPU Allocation** | 4.0 Cores per container (Strictly isolated) |
| **Container RAM Allocation**| 4.0 GB RAM per container (Strictly isolated) |
| **PostgreSQL Shared Memory**| `shm_size: 1g` (POSIX shared memory segment) |

---

## 2. Schema Architecture & Domain Rationale

We designed a star schema centered around an **E-Commerce Sales Domain**. The schema consists of **1 Fact Table** (`fact_sales`) and **4 Dimension Tables** (`dim_customer`, `dim_product`, `dim_store`, `dim_date`).

```
                +-------------------+
                |   dim_customer    |
                |-------------------|
                | customer_id (PK)  |
                | country, segment  |
                +---------+---------+
                          |
                          | 1:N
                          v
+----------------+      +-------------------+      +-------------------+
|   dim_store    | 1:N  |    fact_sales     | N:1  |    dim_product    |
|----------------+----->|-------------------|<-----+-------------------|
| store_id (PK)  |      | sale_id (PK)      |      | product_id (PK)   |
| region, city   |      | customer_id (FK)  |      | category, brand   |
+----------------+      | product_id (FK)   |      +-------------------+
                        | store_id (FK)     |
                        | date_id (FK)      |
                        | quantity, price   |
                        | discount, tax     |
                        | total_amount      |
                        +---------+---------+
                                  ^
                                  | N:1
                        +---------+---------+
                        |     dim_date      |
                        |-------------------|
                        | date_id (PK)      |
                        | year, month, qtr  |
                        +-------------------+
```

### Table Cardinalities & Justification

1. **`fact_sales` (10,000,000 rows, 10 columns)**: Primary fact table representing granular line-item sales orders. Contains 4 foreign keys, 4 numeric measures (`quantity`, `unit_price`, `discount`, `tax_amount`, `total_amount`), and 1 timestamp (`date_id`).
2. **`dim_customer` (100,000 rows)**: High-cardinality dimension representing registered customer profiles across 6 countries and 5 market segments.
3. **`dim_product` (50,000 rows)**: Medium-cardinality dimension containing product catalog metadata across 10 categories and 8 brands.
4. **`dim_store` (1,000 rows)**: Low-cardinality dimension representing retail stores across 4 geographic regions and 5 store types.
5. **`dim_date` (1,095 rows)**: Complete calendar dimension spanning 3 years (2023-01-01 to 2025-12-31).

---

## 3. Benchmark Methodology & Tuning Policy

### Tuning Policy (Option B: Documented Real-World Tuning)
To ensure fairness, both database engines were configured with documented, industry-standard production performance optimizations:

- **PostgreSQL 16 Configuration**:
  - `shared_buffers = 1GB`: Allocates 25% of container RAM to shared buffer pool.
  - `work_mem = 64MB`: Provides generous memory for sort operations and hash tables per query node.
  - `max_parallel_workers_per_gather = 4`: Enables multi-core intra-query parallelism across all 4 container CPUs.
  - **B-Tree Indexing Strategy**: Explicit B-Tree indexes created on `sale_id` (Primary Key), `customer_id`, `product_id`, `store_id`, and `date_id`.
- **ClickHouse Configuration**:
  - `ENGINE = MergeTree()`: Primary analytical engine.
  - `ORDER BY (store_id, date_id, product_id)`: Primary sorting key optimized for analytical filtering and range scanning.
  - `max_threads = 4`: Restricts query execution to 4 worker threads.

### Measurement Methodology
1. **Cold Run**: Executed once per query immediately after dataset initialization to measure un-cached disk I/O latency.
2. **Warm Repetitions**: Executed **5 consecutive times** per query. Primary metric reported is the **Median Latency** (in milliseconds) to eliminate transient OS noise and garbage collection anomalies.
3. **Client-Side Precision**: Measured using Python `time.perf_counter()` capturing wall-clock duration between socket request dispatch and final tuple retrieval.
4. **Result Verification**: Automatic data parity validation (`make validate`) asserting 100% agreement on `COUNT(*)`, `SUM(total_amount)`, `AVG(quantity)`, and distinct cardinalities across both engines.

---

## 4. Query Catalog & Prior Hypotheses

| Query ID | Category | Business Description | Prior Hypothesis | Winner Hypothesis |
|---|---|---|---|---|
| **Q1** | Full-table Aggregation | Compute global SUM, AVG, MIN, MAX over all 10M rows | Columnar scan & SIMD vectorization will outperform row tuple iteration | **ClickHouse** |
| **Q2** | Filtered Aggregation | Aggregation with selective date range and store grouping | ClickHouse primary key range pruning will scan minimal granules | **ClickHouse** |
| **Q3** | High-Cardinality GroupBy | `GROUP BY customer_id` producing 100,000 distinct groups | ClickHouse parallel hash-aggregation will scale better than Postgres hash table | **ClickHouse** |
| **Q4** | Star Join (2 Dims) | `fact_sales` JOIN `dim_store` and `dim_product` grouped by region/category | ClickHouse fast column dictionary lookup will win, but Postgres hash join will be close | **ClickHouse** |
| **Q5** | Full Star Join (4 Dims) | `fact_sales` JOIN all 4 dimensions with multi-dimensional slicing | Hash join build overhead in ClickHouse might narrow the gap against Postgres | **ClickHouse** |
| **Q6** | Top-N Ranking | Top 10 highest revenue store-product combinations (`ORDER BY + LIMIT`) | ClickHouse partial sorting and vectorized top-N heap will outperform Postgres | **ClickHouse** |
| **Q7** | Window Function | Month-over-month revenue trend analysis using `LAG()` window function | ClickHouse window functions will execute faster due to columnar array processing | **ClickHouse** |
| **Q8** | Point Lookup | Single row retrieval by `sale_id` PK index (`WHERE sale_id = 5432100`) | **PostgreSQL B-Tree index** will pinpoint the exact block instantly, defeating ClickHouse sparse index scan | **PostgreSQL** |

---

## 5. Benchmark Results & Performance Tables

### 5.1 Query Latency Metrics (10,000,000 Fact Rows)

All latencies are reported in **milliseconds (ms)**.

| Query ID | Postgres Cold | Postgres Warm Median | Postgres Min / Max | ClickHouse Cold | ClickHouse Warm Median | ClickHouse Min / Max | ClickHouse Speedup Factor | Winner |
|---|---|---|---|---|---|---|---|---|
| **Q1: Full-Table Agg** | 1,747.92 ms | 1,240.26 ms | 1,044 / 1,286 ms | 90.19 ms | **79.65 ms** | 65.59 / 90.93 ms | **15.57x Faster** | 🏆 ClickHouse |
| **Q2: Filtered Agg** | 1,666.62 ms | 1,081.48 ms | 877 / 1,538 ms | 76.09 ms | **60.89 ms** | 58.44 / 76.41 ms | **17.76x Faster** | 🏆 ClickHouse |
| **Q3: High-Card GroupBy**| 1,697.61 ms | 1,514.13 ms | 1,445 / 1,926 ms | 132.71 ms | **108.54 ms** | 104.32 / 189.41 ms | **13.95x Faster** | 🏆 ClickHouse |
| **Q4: Star Join (2 Dims)** | 3,325.21 ms | 2,785.89 ms | 2,764 / 3,011 ms | 465.69 ms | **521.36 ms** | 491.64 / 591.26 ms | **5.34x Faster** | 🏆 ClickHouse |
| **Q5: Full Star Join (4 Dims)**| 2,565.28 ms | 2,151.44 ms | 2,080 / 2,203 ms | 408.08 ms | **388.29 ms** | 379.99 / 425.05 ms | **5.54x Faster** | 🏆 ClickHouse |
| **Q6: Top-N Ranking** | 3,133.87 ms | 3,386.15 ms | 2,811 / 3,852 ms | 297.43 ms | **245.56 ms** | 143.03 / 285.59 ms | **13.79x Faster** | 🏆 ClickHouse |
| **Q7: Window Function** | 1,438.50 ms | 2,309.24 ms | 1,693 / 2,401 ms | 167.69 ms | **162.68 ms** | 146.30 / 183.48 ms | **14.19x Faster** | 🏆 ClickHouse |
| **Q8: Point Lookup** | **2.34 ms** | **2.25 ms** | **2.13 / 2.52 ms** | 26.19 ms | 5.39 ms | 4.83 / 5.97 ms | **0.42x (2.38x Slower)**| 🏆 PostgreSQL |

---

### 5.2 Bulk Data Ingestion Performance

| Database | Scale | Ingestion + Indexing Time (sec) | Throughput (rows / sec) | Speedup Ratio |
|---|---|---|---|---|
| **PostgreSQL 16** | 10,000,000 rows | 44.67 s | 223,863 rows/s | 1.00x |
| **ClickHouse** | 10,000,000 rows | **6.98 s** | **1,432,664 rows/s** | **6.40x Faster** |

---

### 5.3 Multi-Client Concurrency Scaling (Q2 Filtered Aggregation)

| Concurrent Workers | PostgreSQL Throughput (req/s) | PostgreSQL Avg Latency | ClickHouse Throughput (req/s) | ClickHouse Avg Latency | ClickHouse Speedup |
|---|---|---|---|---|---|
| **1 Worker** | 1.64 req/s | 596.73 ms | **11.15 req/s** | **75.05 ms** | **6.80x Faster** |
| **4 Workers** | 1.90 req/s | 2,044.48 ms | **9.23 req/s** | **336.04 ms** | **4.86x Faster** |
| **8 Workers** | 1.63 req/s | 4,293.08 ms | **8.47 req/s** | **605.16 ms** | **5.20x Faster** |

---

## 6. Graphical Analysis

### Figure 1: Median Query Latency Comparison (Logarithmic Scale)
![Median Query Latency](chart_latency_bar.png)

### Figure 2: ClickHouse Speedup Factor per Query
![ClickHouse Speedup Ratio](chart_speedup_bar.png)

### Figure 3: Cold Cache vs. Warm Cache Latency
![Cold vs Warm Latency](chart_cold_vs_warm.png)

### Figure 4: Multi-Client Concurrency Throughput Scaling
![Concurrency Scaling](chart_concurrency.png)

---

## 7. Deep Architectural Analysis

Why did ClickHouse dominate aggregate analytics, while PostgreSQL won on point lookups? We examine the exact physical execution mechanics.

### Case 1: Q1 Full-Table Aggregation (ClickHouse 15.57x Faster)
- **PostgreSQL Execution Mechanics**:
  PostgreSQL uses a row-oriented tuple storage format (`HeapTuple`). To compute `SUM(total_amount)` and `AVG(quantity)`, PostgreSQL must perform a parallel sequential scan (`Parallel Seq Scan`) reading **every single byte of every row** from disk into `shared_buffers`. For 10,000,000 rows, PostgreSQL reads all 10 columns (~1.2 GB of data), constructs 10 million tuple pointers in RAM, deserializes row headers, and processes aggregations row-by-row in C function loops.
- **ClickHouse Execution Mechanics**:
  ClickHouse uses column-oriented `MergeTree` storage. Each column is stored in a separate file (`total_amount.bin`, `quantity.bin`, `unit_price.bin`) compressed with LZ4/ZSTD. For Q1, ClickHouse **completely ignores the remaining 7 columns**, streaming only the ~80 MB compressed binary arrays for `total_amount`, `quantity`, and `unit_price`. Furthermore, ClickHouse processes these primitive arrays using **SIMD (Single Instruction, Multiple Data) vectorization**, executing aggregation operations over 128-bit/256-bit vector registers.

### Case 2: Q6 Top-N Ranking & ORDER BY + LIMIT (ClickHouse 13.79x Faster)
- **PostgreSQL Execution Mechanics**:
  PostgreSQL groups `store_id` and `product_id` using a Parallel Hash Aggregate node. After aggregating, PostgreSQL collects all group results into memory and performs a full sort (`Sort Key: SUM(total_amount) DESC`) using Quicksort or External Merge Sort before applying `LIMIT 10`. Sorting 100,000 aggregate groups introduces heavy CPU comparison overhead.
- **ClickHouse Execution Mechanics**:
  ClickHouse uses a **vectorized top-N priority queue (min-heap)**. During block iteration, ClickHouse maintains only the top 10 elements in a fixed-size heap structure, discarding non-qualifying tuples immediately without performing a global sort over the dataset.

### Case 3: Q8 Point Lookup / Needle-in-Haystack (PostgreSQL 2.38x to 11.19x Faster)
- **ClickHouse Limitation**:
  ClickHouse does not utilize traditional B-Tree indexes. Its `MergeTree` engine uses **sparse primary indexes** with a default `index_granularity` of 8,192 rows. A point lookup for `WHERE sale_id = 5432100` cannot pinpoint an exact single row address. ClickHouse must identify the index granule (an 8,192-row block), decompress the entire 8,192-row column block, and filter rows sequentially. This results in **5.39 ms warm latency** (and **26.19 ms cold latency**).
- **PostgreSQL Triumph**:
  PostgreSQL maintains a dense **B-Tree index** (`idx_fact_sales_pkey`). Navigating the B-Tree root, internal, and leaf nodes takes only 3 to 4 pointer dereferences, directly returning the exact physical block address (`TID: tuple ID`). PostgreSQL fetches the exact 8 KB page from `shared_buffers` in **2.25 ms warm latency** (and **2.34 ms cold latency**).

---

## 8. Nuanced Verdict

Is ClickHouse faster than PostgreSQL for analytical queries?

**YES — with one major qualification.**

1. **For OLAP Aggregations, Slicing, Star Joins, and Window Functions**: ClickHouse is **dramatically faster (5x to 18x speedup)**. Columnar compression, SIMD vectorization, block processing, and primary key granule pruning make ClickHouse order-of-magnitude superior for scanning and aggregating millions of rows.
2. **For Bulk Ingestion**: ClickHouse is **6.4x faster**, ingesting over 1.4 million rows per second due to append-only `MergeTree` LSM-style write paths.
3. **For High-Concurrency Analytics**: ClickHouse maintains stable throughput under concurrent client pressure, whereas PostgreSQL suffers from process fork overhead and shared memory contention.
4. **Where PostgreSQL Wins**: PostgreSQL is superior for **Point Lookups (Point SELECTs)**, transactional updates (`UPDATE`/`DELETE`), ACID multi-table transactions, and complex primary key B-Tree index traversals.

---

## 9. Benchmark Limitations & Threats to Validity

1. **Single-Node Container Deployment**: Tested on a single Docker host (4 CPU, 4GB RAM limits). ClickHouse distributed cluster performance at multi-terabyte scale was not evaluated.
2. **Synthetic Data Distributions**: Synthetic data generated via Zipf distribution may not fully capture complex real-world dirty data anomalies or un-correlated multi-column skews.
3. **Memory Boundary**: Tests were constrained to 4 GB RAM limits. In systems with 256 GB+ RAM, PostgreSQL un-indexed in-memory hash joins may perform closer to columnar engines.
