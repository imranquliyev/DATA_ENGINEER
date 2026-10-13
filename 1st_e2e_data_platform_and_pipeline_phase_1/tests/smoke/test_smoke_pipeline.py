import json
import pytest
from src.common.database import (
    check_infrastructure_health,
    get_postgres_connection,
    get_clickhouse_client,
    get_minio_client
)
from src.common.config import get_settings
from src.orchestration.runner import run_pipeline


@pytest.fixture(scope="session")
def require_infrastructure():
    """Ensures real Docker services are reachable before running smoke tests."""
    health = check_infrastructure_health()
    if not all(health.values()):
        pytest.skip(
            f"Infrastructure services are not ready: {health}. "
            "Please start services via 'docker compose up -d' before running integration smoke tests."
        )


def test_end_to_end_pipeline_slice_and_reconciliation(require_infrastructure):
    """
    Phase 1 Core Smoke Test:
    Triggers the end-to-end pipeline for logical date '2026-10-13',
    asserts that all layers contain data, reconciles row counts,
    and queries the consumer serving interface.
    """
    logical_date = "2026-10-13"
    settings = get_settings()

    # 1. Trigger the orchestrator run
    success = run_pipeline(logical_date=logical_date, fail_ingestion=False)
    assert success is True, "Pipeline run failed to execute end-to-end!"

    # 2. Assert Hop 1: Raw Layer (MinIO S3)
    s3 = get_minio_client()
    raw_key = f"orders/{logical_date}/orders_{logical_date}.json"
    s3_obj = s3.get_object(Bucket=settings.minio_raw_bucket, Key=raw_key)
    raw_orders = json.loads(s3_obj['Body'].read().decode('utf-8'))
    raw_count = len(raw_orders)
    assert raw_count >= 1000, f"Raw orders count ({raw_count}) must be >= 1000"

    # 3. Assert Hop 2: Staging Layer (PostgreSQL)
    pg_conn = get_postgres_connection()
    try:
        with pg_conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM staging.staging_orders WHERE batch_date = %s;",
                (logical_date,)
            )
            staging_count = cur.fetchone()[0]
    finally:
        pg_conn.close()

    assert staging_count >= 1000, f"Staging orders count ({staging_count}) must be >= 1000"
    assert staging_count <= raw_count, "Staging count cannot exceed raw extracted count"
    quarantined_count = raw_count - staging_count

    # 4. Assert Hop 3: Curated Layer (ClickHouse)
    ch = get_clickhouse_client()
    ch_orders_res = ch.query(
        f"SELECT count() FROM fact_delivery_sla FINAL WHERE created_date = toDate('{logical_date}')"
    )
    curated_count = ch_orders_res.result_rows[0][0]
    assert curated_count == staging_count, (
        f"Curated count ({curated_count}) must match valid staging count ({staging_count})"
    )

    # 5. Assert Hop 4: Serving Consumer Layer (ClickHouse Views)
    serving_query = f"""
        SELECT
            sum(total_orders) AS total_orders,
            sum(breached_orders) AS breached_orders,
            count() AS active_routes
        FROM view_daily_hub_sla_summary
        WHERE created_date = toDate('{logical_date}')
    """
    serving_res = list(ch.query(serving_query).named_results())[0]
    served_count = serving_res['total_orders']
    assert served_count == curated_count, (
        f"Serving layer order count ({served_count}) must match curated count ({curated_count})"
    )
    assert serving_res['active_routes'] > 0, "Serving view must return active routes"

    # 6. Report Lineage Reconciliation
    print("\n" + "=" * 65)
    print("📊 PHASE 1 SMOKE TEST — ROW COUNT RECONCILIATION REPORT")
    print("=" * 65)
    print(f"Logical Date:             {logical_date}")
    print(f"1. Raw Storage (MinIO):   {raw_count:>6} rows (s3://{settings.minio_raw_bucket}/{raw_key})")
    print(f"2. Staging DB (Postgres): {staging_count:>6} rows (quarantined {quarantined_count} dirty rows)")
    print(f"3. Curated OLAP (ClickH): {curated_count:>6} rows (fact_delivery_sla)")
    print(f"4. Serving View (ClickH): {served_count:>6} rows (view_daily_hub_sla_summary)")
    print("-" * 65)
    print("Reconciliation Status:    ✅ 100% RECONCILED (Difference = Quarantined by Data Quality)")
    print("=" * 65)


def test_rerun_idempotency(require_infrastructure):
    """
    Asserts that running the pipeline a second time for the SAME logical date
    produces NO duplicate rows at any layer.
    """
    logical_date = "2026-10-13"

    # Get baseline count before second run
    ch = get_clickhouse_client()
    count_before = ch.query(
        f"SELECT count() FROM fact_delivery_sla FINAL WHERE created_date = toDate('{logical_date}')"
    ).result_rows[0][0]

    # Re-run pipeline for same date
    success = run_pipeline(logical_date=logical_date, fail_ingestion=False)
    assert success is True

    # Count after re-run
    count_after = ch.query(
        f"SELECT count() FROM fact_delivery_sla FINAL WHERE created_date = toDate('{logical_date}')"
    ).result_rows[0][0]

    assert count_before == count_after, (
        f"Idempotency violation! Count changed from {count_before} to {count_after} on re-run for {logical_date}"
    )


def test_multi_date_independence(require_infrastructure):
    """
    Asserts that running the pipeline for two different logical dates produces
    data for both, without one overwriting the other.
    """
    date_1 = "2026-10-13"
    date_2 = "2026-10-14"

    # Run for date 2
    success = run_pipeline(logical_date=date_2, fail_ingestion=False)
    assert success is True

    ch = get_clickhouse_client()
    dates_res = ch.query(
        f"""
        SELECT created_date, count()
        FROM fact_delivery_sla FINAL
        WHERE created_date IN (toDate('{date_1}'), toDate('{date_2}'))
        GROUP BY created_date
        ORDER BY created_date
        """
    ).result_rows

    found_dates = [str(r[0]) for r in dates_res]
    assert date_1 in found_dates, f"Date {date_1} was accidentally overwritten!"
    assert date_2 in found_dates, f"Date {date_2} is missing!"
    assert all(r[1] >= 1000 for r in dates_res), "Both dates must contain >= 1000 rows"


def test_deliberate_failure_halts_downstream(require_infrastructure):
    """
    Asserts that activating the deliberate failure switch (FAIL_INGESTION=True)
    stops downstream tasks and marks the orchestrator run as failed.
    """
    logical_date = "2026-10-99"
    success = run_pipeline(logical_date=logical_date, fail_ingestion=True)
    assert success is False, "Deliberate failure switch did not halt pipeline run!"
