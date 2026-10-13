# ADR 001: Phase 1 Batch Walking Skeleton Architecture & Design Decisions

## Status
**Accepted** (2026-10-13)

## Context
Phase 1 of the FastRoute Logistics Data Platform requires constructing a **Walking Skeleton**: an end-to-end, reproducible, orchestrated batch pipeline spanning all layers of the target architecture (`source -> ingestion -> raw storage -> staging -> curated -> serving/consumption`). 

The objective is to prove integration across all infrastructure components and guarantee re-runnability, idempotency, non-trivial volume (>= 1,000 records), and verifiable failure handling.

## Decision

### 1. Ingestion & Raw Storage Partitioning
- **Decision**: The synthetic generator produces batch datasets parameterized by a logical date (`YYYY-MM-DD`). The raw storage uploader writes immutable JSON objects to MinIO S3 under `s3://fastroute-raw/{data_type}/{logical_date}/{data_type}_{logical_date}.json`.
- **Rationale**: Storing raw data partitioned by logical date guarantees that running the pipeline for a specific logical date overwrites or updates that specific date partition without affecting other historical dates.

### 2. Idempotency Pattern across Hops
- **Decision**: We adopted a **Delete-then-Insert** idempotency pattern for PostgreSQL staging (`DELETE FROM staging.staging_orders WHERE batch_date = %s`) and date-partitioned overwrite / `ReplacingMergeTree` for ClickHouse (`ALTER TABLE fact_delivery_sla DELETE WHERE created_date = toDate('%s')`).
- **Rationale**: Running the batch pipeline multiple times for the same logical date leaves the table state duplicate-free. Running for different logical dates appends distinct date partitions.

### 3. Orchestration Task Granularity
- **Decision**: In Apache Airflow 2.8, the pipeline is decomposed into 6 discrete, single-responsibility tasks with explicit linear dependencies:
  1. `1_ingest_source`
  2. `2_raw_storage_landing`
  3. `3_load_staging`
  4. `4_transform_curated`
  5. `5_run_quality_checks`
  6. `6_publish_serving`
- **Rationale**: Violates the anti-pattern of "one giant script task". Allows fine-grained monitoring, targeted retries on ingestion, and explicit failure stopping downstream hops.

### 4. Deliberate Failure Switch Mechanism
- **Decision**: Exposed via `FAIL_INGESTION=true` environment variable or DAG configuration `{"fail_ingestion": true}`. When active, Stage 1 raises a `RuntimeError`, aborting execution immediately.
- **Rationale**: Meets the explicit requirement that a reviewer can trigger a deliberate failure and verify that downstream tasks do not execute and the run is marked as FAILED.

### 5. Automated Quality Gate Strategy
- **Decision**: Curated layer undergoes 5 automated assertions in ClickHouse. If row count is below 1,000, or if primary keys contain nulls or duplicates, a critical `DataQualityFailureError` is thrown, halting pipeline publication and persisting audit logs to PostgreSQL.
- **Rationale**: Validates that quality contracts guard the serving layer against dirty and corrupted upstream inputs.

### 6. Streaming Component Strategy
- **Decision**: Phase 1 implements the full batch slice through MinIO, Postgres staging, ClickHouse OLAP, and Streamlit. Real-time Kafka streaming ingestion for GPS pings is scheduled for Phase 2.
- **Rationale**: Adheres to Phase 1 guidelines prioritizing a complete walking skeleton for batch processing before layering continuous streaming topologies.

## Consequences
- **Positive**: Complete reproducibility, zero manual intervention, single-command smoke test passes cleanly, clean audit trails, and instant reviewer verification.
- **Trade-offs**: Micro-batch latency rather than sub-second streaming for IoT pings (deferred to Phase 2).
