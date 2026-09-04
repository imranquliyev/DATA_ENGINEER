# ClickHouse vs. PostgreSQL — Analytical Query Benchmark

A comprehensive, fully automated, and reproducible benchmark comparing **PostgreSQL 16** (row-oriented OLTP database) and **ClickHouse Latest** (column-oriented OLAP database) on a 10,000,000-row star schema dataset.

---

## 🚀 Quick Start (One Command Execution)

To run the complete benchmark pipeline from scratch (start containers, generate synthetic data, load into both databases, validate data parity, run all benchmark queries, and generate visualization charts):

```bash
make all
```

---

## 🛠️ Individual Makefile Targets

| Target | Description |
|---|---|
| `make up` | Starts PostgreSQL 16 and ClickHouse containers via Docker Compose |
| `make generate` | Generates synthetic star schema datasets (10M and 1M scale) with seed `42` |
| `make load` | Applies DDL schemas and bulk loads CSV data into both databases |
| `make validate` | Verifies exact row counts and aggregate checksum parity across DBs |
| `make benchmark` | Runs 8 core queries (1 cold + 5 warm reps) and multi-client concurrency tests |
| `make report` | Generates visualization charts in `results/` |
| `make down` | Stops containers and cleans up Docker volumes |
| `make help` | Displays available Makefile commands |

---

## 📁 Repository Structure

```
Clickhouse_vs_Postgres_benchmark/
├── docker-compose.yml          # Container orchestration (isolated CPUs, RAM, and shm)
├── Makefile                    # Target runner for end-to-end automation
├── README.md                   # Setup, execution, and architecture guide
├── REPORT.md                   # Full empirical benchmark report & architectural analysis
├── config/
│   ├── postgres.conf           # Postgres OLAP tuning (shared_buffers, work_mem, workers)
│   └── clickhouse.xml          # ClickHouse tuning (thread pool, memory limits)
├── schema/
│   ├── postgres_schema.sql     # DDL DML definitions for PostgreSQL star schema
│   └── clickhouse_schema.sql   # DDL DML definitions for ClickHouse MergeTree schema
├── scripts/
│   ├── generate_data.py        # Deterministic Zipf-skewed data generator (seed=42)
│   ├── load_data.py            # High-performance bulk data loader with timing
│   ├── validate_data.py        # Data parity verifier across DBs
│   ├── run_benchmark.py        # Benchmark suite runner (cold/warm, repetitions, concurrency)
│   └── generate_charts.py      # Chart renderer (latency, speedup, cold vs warm, concurrency)
└── results/
    ├── raw_timings.csv         # Raw execution latencies per iteration
    ├── summary_metrics.json    # Aggregated metrics (medians, mins, maxs, speedups)
    ├── chart_latency_bar.png   # Chart: Median Latency per Query (Log Scale)
    ├── chart_speedup_bar.png   # Chart: ClickHouse Speedup Multiplier
    ├── chart_cold_vs_warm.png  # Chart: Cold vs Warm Cache Latencies
    └── chart_concurrency.png   # Chart: Concurrency Throughput Scaling
```

---

## 💻 System Prerequisites

- **OS**: Linux / macOS
- **Docker**: Version 20.10+ & Docker Compose v2+
- **Python**: 3.10+ (Dependencies managed automatically in `./venv` by Makefile)
- **RAM**: Minimum 8 GB free system memory

---

## 📊 Summary Results Preview

| Query Category | PostgreSQL Median | ClickHouse Median | ClickHouse Speedup Factor | Winner |
|---|---|---|---|---|
| Q1: Full-table Aggregation | 1,240.26 ms | 79.65 ms | **15.57x Faster** | 🏆 ClickHouse |
| Q2: Filtered Aggregation | 1,081.48 ms | 60.89 ms | **17.76x Faster** | 🏆 ClickHouse |
| Q3: High-Cardinality GroupBy | 1,514.13 ms | 108.54 ms | **13.95x Faster** | 🏆 ClickHouse |
| Q4: Star Join (2 Dims) | 2,785.89 ms | 521.36 ms | **5.34x Faster** | 🏆 ClickHouse |
| Q5: Full Star Join (4 Dims) | 2,151.44 ms | 388.29 ms | **5.54x Faster** | 🏆 ClickHouse |
| Q6: Top-N / ORDER BY + LIMIT | 3,386.15 ms | 245.56 ms | **13.79x Faster** | 🏆 ClickHouse |
| Q7: Window Function | 2,309.24 ms | 162.68 ms | **14.19x Faster** | 🏆 ClickHouse |
| Q8: Point Lookup | 2.25 ms | 5.39 ms | **0.42x (2.38x Slower)** | 🏆 PostgreSQL |

*For complete architectural analysis, EXPLAIN query plans, and detailed benchmark methodology, read [REPORT.md](file:///home/imran.quliyev/Documents/DATA_ENGINEER/Clickhouse_vs_Postgres_benchmark/REPORT.md).*
