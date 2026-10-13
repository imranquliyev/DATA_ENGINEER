# FastRoute Logistics — End-to-End Data Platform (Phase 1)

[![Phase 1](https://img.shields.io/badge/Phase%201-Walking%20Skeleton-brightgreen.svg)](#phase-1-definition-of-done)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker%20Compose-2.20%2B-blue.svg)](https://www.docker.com/)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-brightgreen.svg)](.github/workflows/ci.yml)

An end-to-end, reproducible, orchestrated batch pipeline walking skeleton for logistics delivery SLA analytics, driver GPS telemetry monitoring, and automated data quality gating.

---

## 🚚 1. Component-Role Mapping

| Pipeline Component | Assigned Technology | Specific Role in Platform | Phase 1 Status |
| :--- | :--- | :--- | :--- |
| **Data Source & Generator** | Python `LogisticsDataGenerator` | Synthetic package orders & GPS telemetry generator with controlled corruptions | **Implemented** |
| **Raw Storage Landing Lake** | MinIO S3 Object Lake | Immutable S3 raw landing storage partitioned by `logical_date` | **Implemented** |
| **Operational Staging DB** | PostgreSQL 16 | Relational staging layer with delete-then-insert idempotency & audit logging | **Implemented** |
| **Analytical OLAP Warehouse** | ClickHouse 24.3 | Columnar analytical warehouse materializing star schema (`fact_delivery_sla`, `fact_telemetry_pings`) | **Implemented** |
| **Data Quality Gate** | Python `DataQualityValidator` + SQL | Automated assertions (row count >= 1000, not-null, uniqueness) failing bad runs | **Implemented** |
| **Serving & Consumption** | ClickHouse Views & Streamlit UI | Queryable analytical views (`view_daily_hub_sla_summary`) & interactive dashboard | **Implemented** |
| **Orchestrator** | Apache Airflow 2.8 | Orchestrates 6 discrete pipeline tasks with parameterization, retries, and failure gates | **Implemented** |
| **Continuous Streaming Broker**| Apache Kafka | Real-time continuous courier GPS event stream | *Planned for Phase 2* |

---

## 🏛️ 2. Architecture Diagram

```
═══════════════════════════════════════════════════════════════════════════════════
                    PHASE 1 IMPLEMENTED ARCHITECTURE SLICE
═══════════════════════════════════════════════════════════════════════════════════

  [1. INGESTION]          [2. RAW LANDING]          [3. STAGING]
 ┌───────────────┐       ┌─────────────────┐       ┌────────────────┐
 │ Generator /   ├──────►│ MinIO S3 Lake   ├──────►│ PostgreSQL 16  │
 │ External API  │       │ (fastroute-raw) │       │ (staging schema)
 └───────────────┘       └─────────────────┘       └───────┬────────┘
                                                           │
                                                           ▼
  [6. SERVING]            [5. QUALITY GATE]         [4. CURATED OLAP]
 ┌───────────────┐       ┌─────────────────┐       ┌────────────────┐
 │ Streamlit UI  │◄──────┤ Assertions &    │◄──────┤ ClickHouse 24  │
 │ & SQL Views   │       │ Postgres Audit  │       │ (Star Schema)  │
 └───────────────┘       └─────────────────┘       └────────────────┘

       ▲                         ▲                         ▲
       └─────────────────────────┼─────────────────────────┘
                      [APACHE AIRFLOW 2.8 DAG]
            (6 Discrete Tasks with Linear Dependencies)

═══════════════════════════════════════════════════════════════════════════════════
  [PLANNED IN PHASE 2]: Kafka Streaming Broker for Continuous GPS Pings
═══════════════════════════════════════════════════════════════════════════════════
```

---

## 🚀 3. Quick Start & Run the Pipeline

### Prerequisites
- Docker & Docker Compose v2.20+
- Python 3.10+ (for running pytest smoke test locally, or execute inside containers)

### Step 1: Clone & Configure
```bash
git clone https://github.com/imranquliyev/DATA_ENGINEER.git
cd DATA_ENGINEER/1st_e2e_data_platform_and_pipeline_phase_1

# Copy environment variables template (safe defaults out-of-the-box)
cp .env.example .env
```

### Step 2: Spin Up Infrastructure
```bash
# Start all containers in the background
docker compose up -d --build

# Wait until core services are healthy
./scripts/wait_for_services.sh
# or: make wait
```

### Step 3: Trigger the Pipeline Run
Run the 6-stage batch pipeline for a specific logical date:
```bash
# Trigger pipeline for date 2026-10-13 (>= 1,000 rows guaranteed)
make run-pipeline DATE=2026-10-13
# or directly:
python3 -m src.orchestration.runner --date 2026-10-13
```

You can also trigger it directly in **Apache Airflow UI** (`http://localhost:8080`) by opening DAG `fastroute_batch_pipeline` and triggering with config:
```json
{"logical_date": "2026-10-13"}
```

---

## 🧪 4. Automated Integration Smoke Test

Execute the full automated smoke test with a single documented command:
```bash
make smoke
# or:
python3 -m pytest tests/smoke/test_smoke_pipeline.py -s -v
```

### What the Smoke Test Verifies:
1. Connects to **real Docker services** (no mocks).
2. Executes the pipeline end-to-end for logical date `2026-10-13`.
3. Verifies that **every single layer** (Raw, Staging, Curated, Serving) contains non-trivial data (>= 1,000 rows).
4. Prints a full **Row Count Reconciliation Table** across all hops.
5. Verifies **Re-run Idempotency** (re-running the same date produces 0 duplicate rows).
6. Verifies **Multi-date Independence** (running date `2026-10-14` creates both dates without overwrite).
7. Verifies the **Deliberate Failure Switch** halts downstream stages.

---

## 🔍 5. How to Verify Each Architecture Layer

### Hop 1: Raw Storage Landing (MinIO S3)
Verify raw JSON partitions were created:
```bash
# Web UI: http://localhost:9001 (User: minioadmin / Pass: minioadmin)
# S3 CLI check:
docker compose exec minio-create-buckets mc ls localminio/fastroute-raw/orders/2026-10-13/
```
Expected output: `orders_2026-10-13.json` exists with file size > 300KB.

### Hop 2: Operational Staging (PostgreSQL 16)
Verify staging orders and audit logs:
```bash
docker compose exec postgres psql -U fastroute_user -d fastroute_db -c \
  "SELECT batch_date, count(*) AS total_orders FROM staging.staging_orders GROUP BY batch_date;"
```
Expected output: `2026-10-13 | 1140`

### Hop 3: Curated OLAP Warehouse (ClickHouse 24)
Verify fact table row counts and primary key uniqueness:
```bash
docker compose exec clickhouse clickhouse-client -d fastroute_analytics -q \
  "SELECT created_date, count() AS total_rows, uniqExact(order_id) AS unique_ids FROM fact_delivery_sla FINAL GROUP BY created_date;"
```
Expected output: `total_rows == unique_ids` (zero duplicates).

### Hop 4: Serving Consumer View (ClickHouse Serving Layer)
Query the exact consumer serving interface:
```bash
docker compose exec clickhouse clickhouse-client -d fastroute_analytics -q \
  "SELECT origin_hub, dest_hub, total_orders, breached_orders, sla_compliance_pct FROM view_daily_hub_sla_summary LIMIT 5 FORMAT Pretty;"
```

### Hop 5: Interactive Control Center & UI (Streamlit)
Open your browser at:
👉 **[http://localhost:8501](http://localhost:8501)**
- **System Health**: Green status on all 4 components.
- **Pipeline Execution**: Run pipeline or trigger deliberate failure live.
- **Data Layer Explorer**: Visual inspection across all 4 hops.
- **Serving & SLA Analytics**: Interactive route SLA bar charts and driver speed scatter plots.

---

## 💥 6. Deliberate Failure Switch

Phase 1 requires documenting how a reviewer can trigger a deliberate failure and observe that downstream tasks are halted.

### How to Trigger:
```bash
make run-failure DATE=2026-10-13
# or:
python3 -m src.orchestration.runner --date 2026-10-13 --fail-ingestion
```

Or via Airflow UI trigger config:
```json
{"logical_date": "2026-10-13", "fail_ingestion": true}
```

### Expected Observation:
1. Stage 1 (`1_ingest_source`) raises `RuntimeError: Deliberate ingestion failure triggered via FAIL_INGESTION switch`.
2. Downstream tasks (`2_raw_storage_landing` through `6_publish_serving`) are **halted** and **skipped**.
3. In Airflow UI, Stage 1 turns **red (failed)**, downstream tasks turn **orange (upstream_failed)**.
4. CLI runner outputs `❌ PIPELINE RUN FAILED` with non-zero exit code `1`.

---

## 📋 7. Where to View Logs

| Component | How to View Logs | What is Logged |
| :--- | :--- | :--- |
| **Airflow Task Logs** | Airflow UI (`http://localhost:8080`) ➔ Click DAG ➔ Click Task ➔ `Logs` | Start/End time, duration, input location, output location, rows read/written |
| **Pipeline CLI Logs** | Standard output / terminal during `make run-pipeline` | Structured logs formatted with timestamp and stage name |
| **PostgreSQL Staging** | `docker compose logs -f postgres` | SQL queries, connections, init script output |
| **ClickHouse OLAP** | `docker compose logs -f clickhouse` | DDL queries, block inserts, mutations |
| **Data Quality Audit** | `SELECT * FROM audit.quality_audit_logs;` in Postgres | JSON summary of check assertions, passed/failed record tallies |

---

## 🔄 8. Infrastructure Teardown & Restart

```bash
# Stop containers while preserving database volume data
docker compose down

# Restart infrastructure (all data preserved)
docker compose up -d

# Wipe all state clean for a fresh start
docker compose down -v
```

---

## 📦 9. Phase 1 Definition of Done Checklist

- [x] Fresh clone brings up infrastructure and runs pipeline end-to-end using only README commands.
- [x] Every component touched (`source -> ingestion -> raw -> staging -> curated -> serving`).
- [x] 6 separate orchestrated tasks with explicit dependencies; no manual steps.
- [x] Parameterized by logical date and can run for multiple different dates.
- [x] Re-running same logical date produces no duplicates (idempotent).
- [x] Infrastructure restart preserves previous results.
- [x] Deliberate failure stops downstream tasks and marks run failed.
- [x] Smoke test passes with one command (`make smoke`) and reports row counts per layer.
- [x] 5 data quality checks run inside pipeline; failure fails the run.
- [x] Consumer can see serving output (`view_daily_hub_sla_summary` & Streamlit UI).
- [x] CI workflow runs on PR (`.github/workflows/ci.yml`).
- [x] No secrets in code or git history; `.env.example` complete.
- [x] `docs/PROJECT_PLAN.md`, `ADR 001`, and `docs/evidence/phase-1.md` up to date.
- [x] Repository tagged `phase-1`.
