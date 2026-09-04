# FastRoute Logistics — End-to-End Data Platform

[![Phase 0](https://img.shields.io/badge/Phase%200-Completed-brightgreen.svg)](#current-status)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker%20Compose-2.20%2B-blue.svg)](https://www.docker.com/)

An production-grade, reproducible end-to-end data platform built for logistics delivery SLA analytics, courier telemetry monitoring, and automated data quality enforcement.

---

## 🚚 Project Overview
FastRoute Logistics processes thousands of package deliveries across regional fulfillment hubs daily. This platform ingests multi-format operational data (package orders, hub scans, and high-frequency GPS telemetry), cleanses dirty sensor records, enforces data quality contracts, and loads curated analytical star schemas into **ClickHouse** for sub-second SLA insights.

### Key Features
- 🏗️ **Reproducible Infrastructure**: Single-command launch (`docker compose up`) featuring PostgreSQL, MinIO, ClickHouse, Apache Airflow, and Streamlit.
- 🎛️ **Interactive Control Center & UI**: Built-in Web UI (`http://localhost:8501`) to test data generation, run quality checks, inspect raw/staging/curated data, and monitor container health.
- ⚡ **OLAP Analytics**: ClickHouse columnar storage for high-speed SLA aggregations over millions of telemetry rows.
- 🛡️ **Data Quality Enforcement**: Pydantic-based schema validation and audit logging for dirty telemetry records (GPS out-of-bounds, timestamp jitter).
- 🔄 **Automated Orchestration**: Apache Airflow DAGs for scheduled micro-batch processing.

---

## 🏛️ Architecture

```
                                 ┌─────────────────────────┐
                                 │ Synthetic Data Generator│
                                 └────────────┬────────────┘
                                              │ (JSON / Parquet)
                                              ▼
                                 ┌─────────────────────────┐
                                 │  MinIO (S3 Object Lake) │
                                 └────────────┬────────────┘
                                              │
                                              ▼
┌──────────────────────┐         ┌─────────────────────────┐
│ Apache Airflow 2.8   ├────────►│ PostgreSQL 16 (Staging) │
│ (DAG Orchestrator)   │         └────────────┬────────────┘
└──────────────────────┘                      │
                                              ▼
                                 ┌─────────────────────────┐
                                 │ ClickHouse 24 (OLAP)    │
                                 └────────────┬────────────┘
                                              │
                                              ▼
                                 ┌─────────────────────────┐
                                 │ Streamlit Control UI    │
                                 │ (http://localhost:8501) │
                                 └─────────────────────────┘
```

---

## 🛠️ Tech Stack

| Service | Technology | Version | Purpose | URL / Port |
| :--- | :--- | :--- | :--- | :--- |
| **Interactive UI** | Streamlit | `1.32+` | Control panel, testing UI & analytics dashboard | `http://localhost:8501` |
| **Orchestration** | Apache Airflow | `2.8.1` | Workflow scheduling and dependency DAGs | `http://localhost:8080` (airflow/airflow) |
| **Object Storage** | MinIO | `RELEASE.2024` | S3-compatible raw data lake landing | `http://localhost:9001` (minioadmin/minioadmin) |
| **Staging DB** | PostgreSQL | `16-alpine` | Relational operational store & Airflow metadata | `localhost:5432` |
| **OLAP Engine** | ClickHouse | `24.3-alpine` | High-performance analytical column store | `http://localhost:8123` |
| **Language** | Python | `3.10+` | Core ETL pipelines & synthetic data generator | - |

---

## 📁 Directory Structure

```
1st_e2e_data_platform_project/
├── docs/
│   └── PROJECT_PLAN.md            # Detailed 10-section project architecture plan
├── config/
│   ├── postgres/
│   │   └── init.sql               # Staging & audit schema initialization
│   └── clickhouse/
│       └── init.sql               # OLAP star-schema DDL
├── src/
│   ├── common/
│   │   ├── config.py              # Central Pydantic settings management
│   │   ├── database.py            # DB & S3 connection abstraction helpers
│   │   └── logger.py              # Structured logging utility
│   ├── ingestion/
│   │   ├── generator.py           # Realistic synthetic logistics event generator
│   │   └── s3_uploader.py         # MinIO landing layer uploader
│   ├── transformation/
│   │   └── loader.py              # Staging to ClickHouse OLAP transformation pipeline
│   ├── orchestration/
│   │   └── dags/
│   │       └── delivery_pipeline_dag.py # Airflow scheduling DAG
│   ├── quality/
│   │   └── checks.py              # Data quality contracts & audit logger
│   └── ui/
│       └── app.py                 # Streamlit Control Center application
├── tests/
│   ├── test_config.py             # Config management unit tests
│   ├── test_generator.py          # Synthetic generator unit tests
│   └── test_quality.py            # Quality validator unit tests
├── scripts/
│   ├── init_infrastructure.sh     # Infrastructure healthcheck & init helper
│   └── generate_sample_data.py    # CLI data generation utility
├── docker-compose.yml             # Full service stack definition
├── .env.example                   # Central environment variable template
├── .gitignore                     # Git exclusions
├── requirements.txt               # Pinned python dependencies
└── README.md                      # Project documentation
```

---

## 🚀 Quick Start & How to Run

### Prerequisites
- [Docker & Docker Compose](https://docs.docker.com/get-docker/) (v2.20+)
- Python 3.10+ (optional, for local pytest execution)

### 1. Initial Setup
```bash
# Clone the repository
git clone https://github.com/imranquliyev/1st_e2e_data_platform_project.git
cd 1st_e2e_data_platform_project

# Copy environment variables
cp .env.example .env
```

### 2. Start Infrastructure
```bash
# Start all platform services in background
docker compose up -d --build

# Verify all services are healthy
docker compose ps
```

### 3. Open Interactive UI
Open your web browser and navigate to:
👉 **[http://localhost:8501](http://localhost:8501)**

From the Streamlit UI, you can:
1. **Check Infrastructure Status**: Live ping checks for PostgreSQL, MinIO, ClickHouse, and Airflow.
2. **Generate Synthetic Logistics Data**: Interactively trigger package orders and telemetry pings with configurable dirty data injection.
3. **Data Explorer**: Inspect raw MinIO files, PostgreSQL staging tables, and ClickHouse star-schema tables.
4. **SLA Dashboard**: View live interactive delivery SLA breach analytics and driver performance heatmaps.

### 4. Run Automated Tests
```bash
# Run unit tests locally
python3 -m pytest tests/ -v
```

### 5. Stop Infrastructure
```bash
# Stop containers (preserves volume data)
docker compose down

# Stop containers and wipe volume state
docker compose down -v
```

---

## 📊 Current Status
- **Phase 0 (Infrastructure & Project Skeleton)**: ✅ **Completed**
  - Fully reproducible Docker Compose setup with pinned image versions.
  - Complete project layout with runnable Python modules.
  - Centralized environment variables (`.env.example`).
  - Interactive Streamlit Control UI (`http://localhost:8501`).
  - `docs/PROJECT_PLAN.md` fulfilling all Task 0 guidelines.
