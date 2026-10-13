import os
from datetime import datetime
from typing import Dict, Any
from src.common.config import get_settings
from src.common.logger import get_logger
from src.ingestion.generator import LogisticsDataGenerator
from src.ingestion.s3_uploader import MinIOUploader
from src.staging.loader import StagingLoader
from src.transformation.transformer import WarehouseTransformer
from src.quality.checks import DataQualityValidator
from src.serving.publisher import ServingPublisher

logger = get_logger("orchestration_tasks")


def task_ingest_source(logical_date: str, fail_deliberately: bool = False) -> Dict[str, Any]:
    """
    Stage 1: Source Ingestion
    Extracts logistics orders and high-frequency GPS telemetry events from the generator source.
    Deliberate failure switch: if fail_deliberately or FAIL_INGESTION env var is active,
    raises an exception to test failure propagation.
    """
    start_time = datetime.utcnow()
    logger.info("=" * 60)
    logger.info(f"[STAGE 1: INGEST_SOURCE] START at {start_time.isoformat()}")
    logger.info("Input Location: Source Generator (simulated external logistics API / IoT streams)")
    logger.info(f"Logical Date: {logical_date}")

    settings = get_settings()
    env_fail = os.getenv("FAIL_INGESTION", "false").lower() in ("true", "1")
    if fail_deliberately or env_fail:
        logger.error(
            "💥 DELIBERATE FAILURE SWITCH TRIGGERED! Raising RuntimeError to halt pipeline."
        )
        raise RuntimeError(
            "Deliberate ingestion failure triggered via FAIL_INGESTION switch. "
            "Downstream tasks must be stopped and run marked as FAILED."
        )

    generator = LogisticsDataGenerator(
        dirty_rate=settings.dirty_record_rate
    )
    orders = generator.generate_orders(
        count=settings.batch_order_count,
        logical_date=logical_date
    )
    telemetry = generator.generate_telemetry(
        count=settings.batch_telemetry_count,
        logical_date=logical_date
    )

    end_time = datetime.utcnow()
    duration_sec = (end_time - start_time).total_seconds()
    logger.info("Output: In-memory extracted source datasets")
    logger.info(f"Rows Read / Extracted: Orders={len(orders)}, Telemetry={len(telemetry)}")
    logger.info(f"[STAGE 1: INGEST_SOURCE] COMPLETED at {end_time.isoformat()} (Duration: {duration_sec:.2f}s)")
    logger.info("=" * 60)

    return {
        "logical_date": logical_date,
        "orders": orders,
        "telemetry": telemetry,
        "rows_extracted": len(orders) + len(telemetry)
    }


def task_raw_storage_landing(logical_date: str, ingested_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Stage 2: Raw Storage Landing
    Writes raw immutable artifacts directly into MinIO S3 raw buckets partitioned by logical date.
    """
    start_time = datetime.utcnow()
    logger.info("=" * 60)
    logger.info(f"[STAGE 2: RAW_STORAGE_LANDING] START at {start_time.isoformat()}")
    logger.info("Input Location: In-memory extracted records from Stage 1")

    # If invoked directly without pre-ingested data, regenerate for the date
    if ingested_data is None or "orders" not in ingested_data:
        ingested_data = task_ingest_source(logical_date)

    orders = ingested_data["orders"]
    telemetry = ingested_data["telemetry"]

    uploader = MinIOUploader()
    orders_s3 = uploader.upload_batch("orders", orders, logical_date=logical_date)
    telemetry_s3 = uploader.upload_batch("telemetry", telemetry, logical_date=logical_date)

    end_time = datetime.utcnow()
    duration_sec = (end_time - start_time).total_seconds()
    logger.info(f"Output Location 1: {orders_s3}")
    logger.info(f"Output Location 2: {telemetry_s3}")
    logger.info(f"Rows Written to S3: Orders={len(orders)}, Telemetry={len(telemetry)}")
    logger.info(f"[STAGE 2: RAW_STORAGE_LANDING] COMPLETED at {end_time.isoformat()} (Duration: {duration_sec:.2f}s)")
    logger.info("=" * 60)

    return {
        "logical_date": logical_date,
        "orders_s3_uri": orders_s3,
        "telemetry_s3_uri": telemetry_s3,
        "orders_count": len(orders),
        "telemetry_count": len(telemetry)
    }


def task_load_staging(logical_date: str) -> Dict[str, Any]:
    """
    Stage 3: Operational Staging Load
    Reads raw immutable JSON batches from MinIO S3, filters corrupt records,
    and loads into PostgreSQL staging tables with delete-then-insert idempotency.
    """
    start_time = datetime.utcnow()
    logger.info("=" * 60)
    logger.info(f"[STAGE 3: LOAD_STAGING] START at {start_time.isoformat()}")
    logger.info(f"Input Location: MinIO S3 bucket 'fastroute-raw' partition '{logical_date}'")

    loader = StagingLoader()
    orders_stat = loader.load_orders(logical_date=logical_date)
    telemetry_stat = loader.load_telemetry(logical_date=logical_date)

    end_time = datetime.utcnow()
    duration_sec = (end_time - start_time).total_seconds()
    logger.info("Output Location: PostgreSQL staging.staging_orders & staging.staging_telemetry")
    logger.info(
        f"Orders: Read={orders_stat['read']}, Written={orders_stat['written']}, Quarantined={orders_stat['quarantined']}"
    )
    logger.info(
        f"Telemetry: Read={telemetry_stat['read']}, Written={telemetry_stat['written']}, Quarantined={telemetry_stat['quarantined']}"
    )
    logger.info(f"[STAGE 3: LOAD_STAGING] COMPLETED at {end_time.isoformat()} (Duration: {duration_sec:.2f}s)")
    logger.info("=" * 60)

    return {
        "logical_date": logical_date,
        "orders": orders_stat,
        "telemetry": telemetry_stat
    }


def task_transform_curated(logical_date: str) -> Dict[str, Any]:
    """
    Stage 4: Transformation & Curated Warehouse Materialization
    Transforms operational staging data from PostgreSQL and materializes curated
    star-schema fact & dimension tables into ClickHouse OLAP engine.
    """
    start_time = datetime.utcnow()
    logger.info("=" * 60)
    logger.info(f"[STAGE 4: TRANSFORM_CURATED] START at {start_time.isoformat()}")
    logger.info("Input Location: PostgreSQL staging schema (staging_orders, staging_telemetry, couriers, hubs)")

    transformer = WarehouseTransformer()
    dim_stats = transformer.sync_dimensions()
    orders_stat = transformer.transform_and_load_orders(logical_date=logical_date)
    telemetry_stat = transformer.transform_and_load_telemetry(logical_date=logical_date)

    end_time = datetime.utcnow()
    duration_sec = (end_time - start_time).total_seconds()
    logger.info("Output Location: ClickHouse OLAP tables (dim_couriers, dim_hubs, fact_delivery_sla, fact_telemetry_pings)")
    logger.info(f"Dimensions Synced: Couriers={dim_stats['couriers_synced']}, Hubs={dim_stats['hubs_synced']}")
    logger.info(f"Curated Orders: Read={orders_stat['read']}, Written={orders_stat['written']}")
    logger.info(f"Curated Telemetry: Read={telemetry_stat['read']}, Written={telemetry_stat['written']}")
    logger.info(f"[STAGE 4: TRANSFORM_CURATED] COMPLETED at {end_time.isoformat()} (Duration: {duration_sec:.2f}s)")
    logger.info("=" * 60)

    return {
        "logical_date": logical_date,
        "dimensions": dim_stats,
        "orders": orders_stat,
        "telemetry": telemetry_stat
    }


def task_run_quality_checks(logical_date: str) -> Dict[str, Any]:
    """
    Stage 5: Data Quality Gate
    Executes automated quality checks on the curated ClickHouse warehouse tables.
    Fails the pipeline run if critical contracts (row count threshold, non-null, uniqueness) fail.
    """
    start_time = datetime.utcnow()
    logger.info("=" * 60)
    logger.info(f"[STAGE 5: QUALITY_CHECKS] START at {start_time.isoformat()}")
    logger.info(f"Input Location: ClickHouse fact_delivery_sla & fact_telemetry_pings (date={logical_date})")

    validator = DataQualityValidator()
    results = validator.run_curated_checks(logical_date=logical_date)

    end_time = datetime.utcnow()
    duration_sec = (end_time - start_time).total_seconds()
    logger.info("Output Location: PostgreSQL audit.quality_audit_logs")
    logger.info(f"Quality Checks Run: {len(results['checks'])}, Passed={results['passed']}")
    logger.info(f"[STAGE 5: QUALITY_CHECKS] COMPLETED at {end_time.isoformat()} (Duration: {duration_sec:.2f}s)")
    logger.info("=" * 60)

    return results


def task_publish_serving(logical_date: str) -> Dict[str, Any]:
    """
    Stage 6: Serving & Consumption Publication
    Refreshes and verifies analytical consumer views (view_daily_hub_sla_summary,
    view_courier_sla_leaderboard) and reports final summary metrics.
    """
    start_time = datetime.utcnow()
    logger.info("=" * 60)
    logger.info(f"[STAGE 6: PUBLISH_SERVING] START at {start_time.isoformat()}")
    logger.info("Input Location: ClickHouse curated fact tables")

    publisher = ServingPublisher()
    serving_summary = publisher.publish_and_verify(logical_date=logical_date)

    end_time = datetime.utcnow()
    duration_sec = (end_time - start_time).total_seconds()
    logger.info("Output Location: ClickHouse views (view_daily_hub_sla_summary, view_courier_sla_leaderboard) & Streamlit UI")
    logger.info(f"Total Orders Served: {serving_summary['total_orders_served']}")
    logger.info(f"Total Telemetry Pings Served: {serving_summary['total_pings_served']}")
    logger.info(f"[STAGE 6: PUBLISH_SERVING] COMPLETED at {end_time.isoformat()} (Duration: {duration_sec:.2f}s)")
    logger.info("=" * 60)

    return serving_summary
