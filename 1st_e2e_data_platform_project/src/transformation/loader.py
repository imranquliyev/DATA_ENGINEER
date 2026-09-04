from datetime import datetime
from typing import Dict, List
from src.common.database import get_postgres_connection, get_clickhouse_client
from src.common.logger import get_logger

logger = get_logger("transformation_loader")


class PipelineLoader:
    """Loads operational datasets into PostgreSQL staging and ClickHouse OLAP star schema."""

    @staticmethod
    def load_orders_to_postgres(orders: List[Dict]):
        """Loads cleansed orders into PostgreSQL staging schema."""
        if not orders:
            return

        try:
            conn = get_postgres_connection()
            with conn.cursor() as cur:
                for o in orders:
                    cur.execute(
                        """
                        INSERT INTO staging.staging_orders 
                        (order_id, tracking_number, customer_id, origin_hub, dest_hub, package_weight_kg, promised_hours, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (order_id) DO UPDATE SET
                            status = EXCLUDED.status,
                            ingested_at = CURRENT_TIMESTAMP;
                        """,
                        (
                            o["order_id"],
                            o["tracking_number"],
                            o.get("customer_id"),
                            o["origin_hub"],
                            o["dest_hub"],
                            o["package_weight_kg"],
                            o["promised_hours"],
                            o["status"]
                        )
                    )
            conn.commit()
            conn.close()
            logger.info(f"Successfully loaded {len(orders)} orders into PostgreSQL staging")
        except Exception as e:
            logger.error(f"Failed loading orders to PostgreSQL: {e}")
            raise

    @staticmethod
    def load_telemetry_to_clickhouse(pings: List[Dict]):
        """Loads validated telemetry pings into ClickHouse fact_telemetry_pings table."""
        if not pings:
            return

        rows = []
        for p in pings:
            recorded_dt = datetime.fromisoformat(p["recorded_at"])
            rows.append([
                p["ping_id"],
                p["courier_id"],
                float(p["latitude"]),
                float(p["longitude"]),
                float(p["speed_kmh"]),
                int(p["battery_pct"]),
                0,  # is_anomalous = 0 for valid records
                recorded_dt.date(),
                recorded_dt
            ])

        column_names = [
            'ping_id', 'courier_id', 'latitude', 'longitude',
            'speed_kmh', 'battery_pct', 'is_anomalous', 'ping_date', 'recorded_at'
        ]

        try:
            ch = get_clickhouse_client()
            ch.insert('fact_telemetry_pings', rows, column_names=column_names)
            logger.info(f"Successfully loaded {len(pings)} telemetry pings into ClickHouse OLAP")
        except Exception as e:
            logger.error(f"Failed loading telemetry pings to ClickHouse: {e}")
            raise
