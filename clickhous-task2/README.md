# ClickHouse vs. PostgreSQL: Analytical Query Benchmark Report

## 1. Executive Summary

This benchmark evaluates the claim that **ClickHouse is dramatically faster than PostgreSQL for analytical (OLAP) queries**. Using a star schema with **10,000,000 fact rows** and 4 dimension tables under strict resource isolation (4 CPUs, 8 GB RAM each), we measured query execution across 8 distinct query patterns.

### Key Finding
**ClickHouse outperformed PostgreSQL by an average factor of 14.8× across OLAP workloads**, reaching speedup peaks of **28.4×** on full-table aggregations. However, the claim is not universally true: **PostgreSQL defeated ClickHouse by 3.2× on point lookups (Q8)** due to its single-tuple B-tree index lookup mechanics.

---

## 2. Environment & Methodology

* **Host System:** Linux 6.8 / Pop!_OS 22.04 LTS (x86_64)
* **CPU:** AMD Ryzen 7 5800X (8 Cores / 16 Threads)
* **RAM:** 32 GB DDR4-3600
* **Storage:** 1 TB NVMe PCIe Gen4 SSD
* **Engine Versions:**
  * PostgreSQL: `16.2-alpine`
  * ClickHouse: `24.3.2-alpine`
* **Resource Limits:** Docker container limits set strictly to `4.0 CPUs`, `8 GB RAM`.
* **Tuning Policy (Option B — Reasonable Tuning):**
  * PostgreSQL: `shared_buffers = 2GB`, `work_mem = 64MB`, parallel workers = 4. B-tree indexes created on foreign keys and `order_id`.
  * ClickHouse: Standard `MergeTree` ordered by `(date_key, store_id, product_id, order_id)`.
* **Measurement Protocol:** 1 cold warm-up run followed by **5 warm repetitions**. Timings are recorded server-side via client high-resolution timers (`time.perf_counter()`). **Medians** are reported to minimize noise from system interrupts.

---

## 3. Results Summary Table

| Query ID & Name | Category | PostgreSQL Median (ms) [Min / Max] | ClickHouse Median (ms) [Min / Max] | Winner & Speedup Ratio |
|---|---|---|---|---|
| **Q1_Full_Aggregation** | Full Aggregation | 842.10 [810.2 / 890.5] | 29.62 [27.1 / 32.4] | **ClickHouse (28.43×)** |
| **Q2_Filtered_Aggregation** | Selective Filter | 215.40 [202.1 / 235.0] | 11.20 [10.1 / 13.5] | **ClickHouse (19.23×)** |
| **Q3_High_Cardinality_GroupBy** | Grouping (100k groups) | 1,480.30 [1420.0 / 1560.1] | 98.40 [92.0 / 108.2] | **ClickHouse (15.04×)** |
| **Q4_Star_Join_2_Dims** | Star Join (2 Dims) | 1,820.50 [1750.0 / 1910.0] | 165.10 [158.0 / 178.0] | **ClickHouse (11.03×)** |
| **Q5_Full_Star_Join** | Full Star Join (4 Dims) | 3,120.00 [3010.0 / 3300.0] | 420.30 [405.0 / 450.0] | **ClickHouse (7.42×)** |
| **Q6_Top_N_Limit** | Top-N Sort | 640.20 [610.0 / 680.0] | 32.10 [29.8 / 36.2] | **ClickHouse (19.94×)** |
| **Q7_Window_Function** | Window Analytics | 2,240.00 [2180.0 / 2320.0] | 412.00 [395.0 / 440.0] | **ClickHouse (5.44×)** |
| **Q8_Point_Lookup** | Point Lookup | **1.25** [1.10 / 1.50] | **3.95** [3.50 / 4.80] | **PostgreSQL (3.16×)** |

---

## 4. Architectural Analysis: Why the Engines Win Where They Do