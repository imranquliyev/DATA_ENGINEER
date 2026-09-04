import json
from typing import Dict, List, Tuple
from src.common.database import get_postgres_connection
from src.common.logger import get_logger

logger = get_logger("quality_checks")


class DataQualityValidator:
    """Enforces data quality contracts on raw datasets and records quarantine logs."""

    @staticmethod
    def validate_telemetry_batch(pings: List[Dict]) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        Validates telemetry pings:
        - Lat must be in [-90, 90] and not 0.0
        - Lon must be in [-180, 180] and not 0.0
        - Speed must be >= 0.0
        """
        valid_records = []
        invalid_records = []
        reasons = {}

        for p in pings:
            failures = []
            lat = p.get("latitude", 0.0)
            lon = p.get("longitude", 0.0)
            speed = p.get("speed_kmh", 0.0)

            if lat == 0.0 or lat < -90.0 or lat > 90.0:
                failures.append("INVALID_LATITUDE")
            if lon == 0.0 or lon < -180.0 or lon > 180.0:
                failures.append("INVALID_LONGITUDE")
            if speed < 0.0:
                failures.append("NEGATIVE_SPEED")

            if failures:
                p_copy = dict(p)
                p_copy["rejection_reasons"] = failures
                invalid_records.append(p_copy)
                for r in failures:
                    reasons[r] = reasons.get(r, 0) + 1
            else:
                valid_records.append(p)

        metrics = {
            "total": len(pings),
            "passed": len(valid_records),
            "failed": len(invalid_records),
            "reasons": reasons
        }

        logger.info(f"Telemetry quality validation complete: {metrics['passed']}/{metrics['total']} passed")
        return valid_records, invalid_records, metrics

    @staticmethod
    def validate_orders_batch(orders: List[Dict]) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        Validates package orders:
        - order_id and tracking_number must be non-empty
        - status must be valid enum
        """
        valid_enums = {"CREATED", "DISPATCHED", "IN_TRANSIT", "DELIVERED", "FAILED_ATTEMPT"}
        valid_records = []
        invalid_records = []
        reasons = {}

        for o in orders:
            failures = []
            if not o.get("order_id") or not o.get("tracking_number"):
                failures.append("MISSING_KEYS")
            if o.get("status") not in valid_enums:
                failures.append("INVALID_STATUS_ENUM")

            if failures:
                o_copy = dict(o)
                o_copy["rejection_reasons"] = failures
                invalid_records.append(o_copy)
                for r in failures:
                    reasons[r] = reasons.get(r, 0) + 1
            else:
                valid_records.append(o)

        metrics = {
            "total": len(orders),
            "passed": len(valid_records),
            "failed": len(invalid_records),
            "reasons": reasons
        }

        logger.info(f"Orders quality validation complete: {metrics['passed']}/{metrics['total']} passed")
        return valid_records, invalid_records, metrics

    @staticmethod
    def log_audit_to_postgres(batch_id: str, dataset_name: str, metrics: Dict):
        """Persists data quality metrics into PostgreSQL audit table."""
        try:
            conn = get_postgres_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit.quality_audit_logs 
                    (batch_id, dataset_name, total_records, passed_records, failed_records, failure_reasons)
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (
                        batch_id,
                        dataset_name,
                        metrics["total"],
                        metrics["passed"],
                        metrics["failed"],
                        json.dumps(metrics["reasons"])
                    )
                )
            conn.commit()
            conn.close()
            logger.info(f"Persisted audit metrics to PostgreSQL for batch {batch_id}")
        except Exception as e:
            logger.warning(f"Could not log audit metrics to PostgreSQL (db offline?): {e}")
