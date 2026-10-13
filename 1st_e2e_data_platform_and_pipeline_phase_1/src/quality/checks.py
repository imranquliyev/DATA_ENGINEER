import json
from typing import Dict, List
from src.common.database import get_clickhouse_client, get_postgres_connection
from src.common.logger import get_logger

logger = get_logger("quality_checks")


class DataQualityFailureError(Exception):
    """Raised when a critical data quality check fails, halting pipeline execution."""
    pass


class DataQualityValidator:
    """
    Enforces data quality contracts on curated OLAP tables in ClickHouse.
    Runs 5 automated quality checks (>= 3 required by Phase 1 specification).
    Configured to fail the pipeline run if critical checks are violated.
    """

    def __init__(self):
        self.ch = get_clickhouse_client()

    def run_curated_checks(self, logical_date: str) -> Dict:
        """
        Executes automated quality checks on ClickHouse curated layer for logical_date:
        1. Row Count Check (Volume >= 1000) [CRITICAL]
        2. Non-Null Primary Key Check (order_id NOT NULL) [CRITICAL]
        3. Uniqueness Check (order_id is unique, no duplicates) [CRITICAL]
        4. Coordinate Range Sanity Check (lat/lon within valid bounds) [CRITICAL]
        5. SLA Hours Sanity Check (actual_hours > 0)
        """
        logger.info(f"Running curated data quality checks for logical_date={logical_date}...")
        results = {
            "logical_date": logical_date,
            "checks": [],
            "passed": True
        }

        # Query 1: Orders Quality Metrics
        orders_query = f"""
            SELECT
                count() AS total_rows,
                countIf(order_id IS NULL OR order_id = '') AS null_keys,
                uniqExact(order_id) AS unique_keys,
                countIf(actual_hours <= 0) AS invalid_hours
            FROM fact_delivery_sla FINAL
            WHERE created_date = toDate('{logical_date}')
        """
        order_metrics = list(self.ch.query(orders_query).named_results())[0]
        total_orders = order_metrics['total_rows']
        null_keys = order_metrics['null_keys']
        unique_keys = order_metrics['unique_keys']
        invalid_hours = order_metrics['invalid_hours']

        # Query 2: Telemetry Quality Metrics
        telemetry_query = f"""
            SELECT
                count() AS total_pings,
                countIf(latitude < -90.0 OR latitude > 90.0 OR longitude < -180.0 OR longitude > 180.0 OR (latitude = 0 AND longitude = 0)) AS corrupt_gps,
                countIf(speed_kmh < 0) AS negative_speed
            FROM fact_telemetry_pings FINAL
            WHERE ping_date = toDate('{logical_date}')
        """
        telemetry_metrics = list(self.ch.query(telemetry_query).named_results())[0]
        total_pings = telemetry_metrics['total_pings']
        corrupt_gps = telemetry_metrics['corrupt_gps']
        negative_speed = telemetry_metrics['negative_speed']

        # --- Check 1: Row Count Check (>= 1,000 rows) ---
        chk1_pass = total_orders >= 1000
        results["checks"].append({
            "name": "ROW_COUNT_MINIMUM_THRESHOLD",
            "table": "fact_delivery_sla",
            "condition": f"total_orders ({total_orders}) >= 1000",
            "passed": chk1_pass,
            "critical": True
        })

        # --- Check 2: Non-Null Primary Key Check ---
        chk2_pass = (null_keys == 0)
        results["checks"].append({
            "name": "NOT_NULL_PRIMARY_KEY",
            "table": "fact_delivery_sla",
            "condition": f"null order_id count ({null_keys}) == 0",
            "passed": chk2_pass,
            "critical": True
        })

        # --- Check 3: Uniqueness on Primary Key Check ---
        duplicate_count = total_orders - unique_keys
        chk3_pass = (duplicate_count == 0)
        results["checks"].append({
            "name": "PRIMARY_KEY_UNIQUENESS",
            "table": "fact_delivery_sla",
            "condition": f"duplicate keys ({duplicate_count}) == 0",
            "passed": chk3_pass,
            "critical": True
        })

        # --- Check 4: Coordinate Range Sanity Check ---
        chk4_pass = (corrupt_gps == 0 and negative_speed == 0)
        results["checks"].append({
            "name": "TELEMETRY_COORDINATES_AND_SPEED_BOUNDS",
            "table": "fact_telemetry_pings",
            "condition": f"corrupt gps ({corrupt_gps}) == 0 and negative speed ({negative_speed}) == 0",
            "passed": chk4_pass,
            "critical": True
        })

        # --- Check 5: SLA Hours Sanity Check ---
        chk5_pass = (invalid_hours == 0)
        results["checks"].append({
            "name": "POSITIVE_ACTUAL_HOURS",
            "table": "fact_delivery_sla",
            "condition": f"invalid hours count ({invalid_hours}) == 0",
            "passed": chk5_pass,
            "critical": False
        })

        # Evaluate critical check failures
        failed_critical = [c for c in results["checks"] if not c["passed"] and c["critical"]]
        if failed_critical:
            results["passed"] = False
            error_msg = f"Data quality validation FAILED: {len(failed_critical)} critical check(s) violated: {failed_critical}"
            logger.error(error_msg)
            self._log_audit_to_postgres(logical_date, "fact_delivery_sla", total_orders, 0, len(failed_critical), results["checks"])
            raise DataQualityFailureError(error_msg)

        logger.info(
            f"All {len(results['checks'])} data quality checks PASSED for logical_date={logical_date} (orders={total_orders}, pings={total_pings})"
        )
        self._log_audit_to_postgres(logical_date, "fact_delivery_sla", total_orders, total_orders, 0, results["checks"])
        return results

    def _log_audit_to_postgres(self, logical_date: str, dataset_name: str, total: int, passed: int, failed: int, details: List[Dict]):
        """Persists data quality audit log into PostgreSQL."""
        try:
            conn = get_postgres_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit.quality_audit_logs 
                    (batch_id, logical_date, dataset_name, total_records, passed_records, failed_records, failure_reasons)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        f"DQ-{logical_date}",
                        logical_date,
                        dataset_name,
                        total,
                        passed,
                        failed,
                        json.dumps(details)
                    )
                )
            conn.commit()
            conn.close()
            logger.info(f"Persisted data quality audit record to PostgreSQL for {logical_date}")
        except Exception as e:
            logger.warning(f"Could not persist audit record to PostgreSQL: {e}")
