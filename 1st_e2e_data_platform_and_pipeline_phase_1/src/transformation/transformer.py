from datetime import datetime
from typing import Dict
from src.common.database import get_postgres_connection, get_clickhouse_client
from src.common.logger import get_logger

logger = get_logger("transformation_warehouse")


class WarehouseTransformer:
    """
    Transforms cleansed staging data from PostgreSQL and materializes curated OLAP star schema
    in ClickHouse (dim_couriers, dim_hubs, fact_delivery_sla, fact_telemetry_pings).
    Ensures date-scoped idempotency for repeatable executions.
    """

    def __init__(self):
        self.ch = get_clickhouse_client()

    def sync_dimensions(self) -> Dict[str, int]:
        """Syncs dimension tables from PostgreSQL into ClickHouse."""
        pg_conn = get_postgres_connection()
        try:
            with pg_conn.cursor() as cur:
                # 1. Sync Couriers
                cur.execute("SELECT courier_id, full_name, vehicle_type, home_hub, active_status FROM staging.couriers;")
                courier_rows = cur.fetchall()

                courier_data = [
                    [r[0], r[1], r[2], r[3], 1 if r[4] else 0, datetime.utcnow()]
                    for r in courier_rows
                ]
                if courier_data:
                    self.ch.insert(
                        'dim_couriers',
                        courier_data,
                        column_names=['courier_id', 'full_name', 'vehicle_type', 'home_hub', 'active_status', 'updated_at']
                    )

                # 2. Sync Hubs
                cur.execute("SELECT hub_id, hub_name, city, latitude, longitude FROM staging.hubs;")
                hub_rows = cur.fetchall()

                hub_data = [
                    [r[0], r[1], r[2], float(r[3]), float(r[4]), datetime.utcnow()]
                    for r in hub_rows
                ]
                if hub_data:
                    self.ch.insert(
                        'dim_hubs',
                        hub_data,
                        column_names=['hub_id', 'hub_name', 'city', 'latitude', 'longitude', 'updated_at']
                    )

            logger.info(f"Dimensions synced: {len(courier_data)} couriers, {len(hub_data)} hubs")
            return {
                "couriers_synced": len(courier_data),
                "hubs_synced": len(hub_data)
            }
        finally:
            pg_conn.close()

    def transform_and_load_orders(self, logical_date: str) -> Dict[str, int]:
        """
        Extracts staging orders for the logical date, calculates SLA breach flags,
        and loads into ClickHouse fact_delivery_sla.
        """
        pg_conn = get_postgres_connection()
        try:
            with pg_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT order_id, tracking_number, customer_id, origin_hub, dest_hub,
                           package_weight_kg, promised_hours, status, created_at
                    FROM staging.staging_orders
                    WHERE batch_date = %s;
                    """,
                    (logical_date,)
                )
                rows = cur.fetchall()
        finally:
            pg_conn.close()

        if not rows:
            logger.warning(f"No staging orders found for logical_date={logical_date}")
            return {"read": 0, "written": 0}

        target_date = datetime.strptime(logical_date, "%Y-%m-%d").date()
        fact_rows = []
        for r in rows:
            promised = int(r[6])
            # Simulated naive delivery duration logic for Phase 1
            # Actual hours calculated based on order id hash for reproducibility
            salt = int(r[0].split("-")[-1]) if "-" in r[0] and r[0].split("-")[-1].isdigit() else 10
            actual_hours = round(promised * 0.85 + (salt % 15) * 1.5, 2)
            is_sla_breached = 1 if actual_hours > promised else 0

            created_dt = r[8] if isinstance(r[8], datetime) else datetime.utcnow()
            delivered_dt = created_dt  # Naive placeholder for Phase 1

            fact_rows.append([
                r[0],                                 # order_id
                r[1],                                 # tracking_number
                r[2] or "CUST-ANON",                  # customer_id
                r[3],                                 # origin_hub
                r[4],                                 # dest_hub
                float(r[5] or 0.0),                   # package_weight_kg
                promised,                             # promised_hours
                actual_hours,                         # actual_hours
                is_sla_breached,                      # is_sla_breached
                r[7],                                 # delivery_status
                target_date,                          # created_date
                created_dt.replace(tzinfo=None),      # created_at
                delivered_dt.replace(tzinfo=None),    # delivered_at
                datetime.utcnow()                     # updated_at
            ])

        # ClickHouse idempotency: delete records for this created_date synchronously before insert
        try:
            self.ch.command(
                f"ALTER TABLE fact_delivery_sla DELETE WHERE created_date = toDate('{logical_date}')",
                settings={'mutations_sync': 1}
            )
        except Exception as e:
            logger.debug(f"ClickHouse DELETE notice: {e}")

        columns = [
            'order_id', 'tracking_number', 'customer_id', 'origin_hub', 'dest_hub',
            'package_weight_kg', 'promised_hours', 'actual_hours', 'is_sla_breached',
            'delivery_status', 'created_date', 'created_at', 'delivered_at', 'updated_at'
        ]
        self.ch.insert('fact_delivery_sla', fact_rows, column_names=columns)

        logger.info(
            f"Curated fact_delivery_sla loaded: {len(fact_rows)} rows inserted into ClickHouse (logical_date={logical_date})"
        )
        return {"read": len(rows), "written": len(fact_rows)}

    def transform_and_load_telemetry(self, logical_date: str) -> Dict[str, int]:
        """
        Extracts staging telemetry for logical date and loads into ClickHouse fact_telemetry_pings.
        """
        pg_conn = get_postgres_connection()
        try:
            with pg_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ping_id, courier_id, latitude, longitude, speed_kmh, battery_pct, recorded_at
                    FROM staging.staging_telemetry
                    WHERE batch_date = %s;
                    """,
                    (logical_date,)
                )
                rows = cur.fetchall()
        finally:
            pg_conn.close()

        if not rows:
            logger.warning(f"No staging telemetry found for logical_date={logical_date}")
            return {"read": 0, "written": 0}

        target_date = datetime.strptime(logical_date, "%Y-%m-%d").date()
        fact_rows = []
        for r in rows:
            recorded_dt = r[6] if isinstance(r[6], datetime) else datetime.utcnow()
            fact_rows.append([
                r[0],                               # ping_id
                r[1],                               # courier_id
                float(r[2]),                        # latitude
                float(r[3]),                        # longitude
                float(r[4]),                        # speed_kmh
                int(r[5]),                          # battery_pct
                0,                                  # is_anomalous (valid cleansed subset)
                target_date,                        # ping_date
                recorded_dt.replace(tzinfo=None),   # recorded_at
                datetime.utcnow()                   # updated_at
            ])

        try:
            self.ch.command(
                f"ALTER TABLE fact_telemetry_pings DELETE WHERE ping_date = toDate('{logical_date}')",
                settings={'mutations_sync': 1}
            )
        except Exception as e:
            logger.debug(f"ClickHouse DELETE notice: {e}")

        columns = [
            'ping_id', 'courier_id', 'latitude', 'longitude', 'speed_kmh',
            'battery_pct', 'is_anomalous', 'ping_date', 'recorded_at', 'updated_at'
        ]
        self.ch.insert('fact_telemetry_pings', fact_rows, column_names=columns)

        logger.info(
            f"Curated fact_telemetry_pings loaded: {len(fact_rows)} rows inserted into ClickHouse (logical_date={logical_date})"
        )
        return {"read": len(rows), "written": len(fact_rows)}
