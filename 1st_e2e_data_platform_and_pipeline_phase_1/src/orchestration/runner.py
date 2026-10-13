import argparse
import sys
from datetime import datetime
from src.common.logger import get_logger
from src.orchestration.tasks import (
    task_ingest_source,
    task_raw_storage_landing,
    task_load_staging,
    task_transform_curated,
    task_run_quality_checks,
    task_publish_serving
)

logger = get_logger("orchestration_runner")


def run_pipeline(logical_date: str, fail_ingestion: bool = False) -> bool:
    """
    Executes the 6-stage batch pipeline sequentially for a given logical date.
    Returns True if completed successfully, False if failed.
    """
    pipeline_start = datetime.utcnow()
    logger.info("****************************************************************")
    logger.info("🚀 INITIATING FASTROUTE LOGISTICS BATCH PIPELINE")
    logger.info(f"   Logical Date: {logical_date}")
    logger.info(f"   Fail Ingestion Switch: {fail_ingestion}")
    logger.info(f"   Started At: {pipeline_start.isoformat()}")
    logger.info("****************************************************************")

    try:
        # Stage 1: Ingestion
        ingest_res = task_ingest_source(logical_date=logical_date, fail_deliberately=fail_ingestion)

        # Stage 2: Raw Storage Landing
        raw_res = task_raw_storage_landing(logical_date=logical_date, ingested_data=ingest_res)

        # Stage 3: Load Staging
        staging_res = task_load_staging(logical_date=logical_date)

        # Stage 4: Transform Curated
        curated_res = task_transform_curated(logical_date=logical_date)

        # Stage 5: Quality Gate
        quality_res = task_run_quality_checks(logical_date=logical_date)

        # Stage 6: Publish Serving
        serving_res = task_publish_serving(logical_date=logical_date)

        pipeline_end = datetime.utcnow()
        duration = (pipeline_end - pipeline_start).total_seconds()

        logger.info("****************************************************************")
        logger.info(f"✅ PIPELINE RUN COMPLETED SUCCESSFULLY in {duration:.2f}s")
        logger.info(f"   Logical Date: {logical_date}")
        logger.info(f"   Raw Orders Landed: {raw_res['orders_count']}")
        logger.info(f"   Staging Orders Written: {staging_res['orders']['written']} (Quarantined: {staging_res['orders']['quarantined']})")
        logger.info(f"   Curated Orders Written: {curated_res['orders']['written']}")
        logger.info(f"   Serving Orders Reported: {serving_res['total_orders_served']}")
        logger.info(f"   Quality Checks: {len(quality_res['checks'])} passed")
        logger.info("****************************************************************")
        return True

    except Exception as e:
        pipeline_end = datetime.utcnow()
        duration = (pipeline_end - pipeline_start).total_seconds()
        logger.error("****************************************************************")
        logger.error(f"❌ PIPELINE RUN FAILED after {duration:.2f}s!")
        logger.error(f"   Error: {e}")
        logger.error("   Downstream stages were HALTED.")
        logger.error("****************************************************************")
        return False


def main():
    parser = argparse.ArgumentParser(description="FastRoute Logistics Phase 1 Batch Pipeline CLI Runner")
    parser.add_argument(
        "--date",
        type=str,
        default="2026-10-13",
        help="Logical date / partition for the pipeline run (format: YYYY-MM-DD)"
    )
    parser.add_argument(
        "--fail-ingestion",
        action="store_true",
        help="Deliberately trigger an ingestion failure to verify error handling"
    )

    args = parser.parse_args()
    success = run_pipeline(logical_date=args.date, fail_ingestion=args.fail_ingestion)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
