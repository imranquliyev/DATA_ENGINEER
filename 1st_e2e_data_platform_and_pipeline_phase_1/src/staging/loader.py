from typing import Dict, List, Tuple
from src.common.database import get_postgres_connection
from src.common.logger import get_logger
from src.ingestion.s3_uploader import MinIOUploader

logger = get_logger("staging_loader")

VALID_STATUSES = {"CREATED", "DISPATCHED", "IN_TRANSIT", "DELIVERED", "FAILED_ATTEMPT"}


class StagingLoader:
    """
    Loads raw operational data from MinIO S3 into PostgreSQL operational staging tables.
    Implements delete-then-insert idempotency keyed by logical batch date.
    """

    def __init__(self):
        self._s3_uploader = None

    @property
    def s3_uploader(self):
        if self._s3_uploader is None:
            self._s3_uploader = MinIOUploader()
        return self._s3_uploader

    def filter_orders(self, raw_orders: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Separates valid orders from corrupt records."""
        valid, quarantined = [], []
        for o in raw_orders:
            if not o.get("order_id") or not o.get("tracking_number"):
                quarantined.append(o)
            elif o.get("status") not in VALID_STATUSES:
                quarantined.append(o)
            else:
                valid.append(o)
        return valid, quarantined

    def filter_telemetry(self, raw_pings: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Separates valid telemetry pings from corrupt records."""
        valid, quarantined = [], []
        for p in raw_pings:
            lat = p.get("latitude", 0.0)
            lon = p.get("longitude", 0.0)
            speed = p.get("speed_kmh", 0.0)

            if lat == 0.0 or lat < -90.0 or lat > 90.0:
                quarantined.append(p)
            elif lon == 0.0 or lon < -180.0 or lon > 180.0:
                quarantined.append(p)
            elif speed < 0.0:
                quarantined.append(p)
            else:
                valid.append(p)
        return valid, quarantined

    def load_orders(self, logical_date: str) -> Dict[str, int]:
        """
        Loads orders from MinIO S3 into staging.staging_orders using delete-then-insert.
        """
        raw_orders = self.s3_uploader.read_batch("orders", logical_date)
        valid_orders, quarantined = self.filter_orders(raw_orders)

        conn = get_postgres_connection()
        try:
            with conn.cursor() as cur:
                # Idempotent cleanup for this logical date partition
                cur.execute(
                    "DELETE FROM staging.staging_orders WHERE batch_date = %s;",
                    (logical_date,)
                )

                # Batch insert valid records
                insert_query = """
                    INSERT INTO staging.staging_orders 
                    (order_id, tracking_number, customer_id, origin_hub, dest_hub, 
                     package_weight_kg, promised_hours, status, created_at, batch_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                records_to_insert = [
                    (
                        o["order_id"],
                        o["tracking_number"],
                        o.get("customer_id") or "CUST-ANON",
                        o["origin_hub"],
                        o["dest_hub"],
                        o["package_weight_kg"],
                        o["promised_hours"],
                        o["status"],
                        o["created_at"],
                        logical_date
                    )
                    for o in valid_orders
                ]
                cur.executemany(insert_query, records_to_insert)

            conn.commit()
            logger.info(
                f"Staging orders loaded: {len(valid_orders)} inserted, {len(quarantined)} quarantined (batch_date={logical_date})"
            )
            return {
                "read": len(raw_orders),
                "written": len(valid_orders),
                "quarantined": len(quarantined)
            }
        finally:
            conn.close()

    def load_telemetry(self, logical_date: str) -> Dict[str, int]:
        """
        Loads telemetry pings from MinIO S3 into staging.staging_telemetry using delete-then-insert.
        """
        raw_pings = self.s3_uploader.read_batch("telemetry", logical_date)
        valid_pings, quarantined = self.filter_telemetry(raw_pings)

        conn = get_postgres_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM staging.staging_telemetry WHERE batch_date = %s;",
                    (logical_date,)
                )

                insert_query = """
                    INSERT INTO staging.staging_telemetry
                    (ping_id, courier_id, latitude, longitude, speed_kmh, battery_pct, recorded_at, batch_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                records_to_insert = [
                    (
                        p["ping_id"],
                        p["courier_id"],
                        p["latitude"],
                        p["longitude"],
                        p["speed_kmh"],
                        p["battery_pct"],
                        p["recorded_at"],
                        logical_date
                    )
                    for p in valid_pings
                ]
                cur.executemany(insert_query, records_to_insert)

            conn.commit()
            logger.info(
                f"Staging telemetry loaded: {len(valid_pings)} inserted, {len(quarantined)} quarantined (batch_date={logical_date})"
            )
            return {
                "read": len(raw_pings),
                "written": len(valid_pings),
                "quarantined": len(quarantined)
            }
        finally:
            conn.close()
