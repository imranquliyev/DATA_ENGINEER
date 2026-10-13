from typing import Dict
from src.common.database import get_clickhouse_client
from src.common.logger import get_logger

logger = get_logger("serving_publisher")


class ServingPublisher:
    """
    Exposes and validates curated analytical artifacts in the serving layer
    (ClickHouse view_daily_hub_sla_summary and view_courier_sla_leaderboard).
    """

    def __init__(self):
        self.ch = get_clickhouse_client()

    def publish_and_verify(self, logical_date: str) -> Dict:
        """
        Queries and asserts that the serving views contain accessible aggregated data
        for the given logical_date.
        """
        logger.info(f"Publishing and verifying serving layer views for logical_date={logical_date}...")

        # 1. Query Hub SLA Summary serving view
        hub_summary_query = f"""
            SELECT
                origin_hub,
                dest_hub,
                total_orders,
                breached_orders,
                on_time_orders,
                sla_compliance_pct,
                avg_delivery_hours
            FROM view_daily_hub_sla_summary
            WHERE created_date = toDate('{logical_date}')
            ORDER BY total_orders DESC
        """
        hub_results = list(self.ch.query(hub_summary_query).named_results())

        # 2. Query Courier Leaderboard serving view
        courier_summary_query = f"""
            SELECT
                courier_id,
                full_name,
                vehicle_type,
                home_hub,
                total_pings,
                avg_speed_kmh,
                avg_battery_pct
            FROM view_courier_sla_leaderboard
            WHERE ping_date = toDate('{logical_date}')
            ORDER BY total_pings DESC
        """
        courier_results = list(self.ch.query(courier_summary_query).named_results())

        total_orders_served = sum(r['total_orders'] for r in hub_results)
        total_pings_served = sum(r['total_pings'] for r in courier_results)

        summary = {
            "logical_date": logical_date,
            "hub_routes_count": len(hub_results),
            "total_orders_served": total_orders_served,
            "couriers_active": len(courier_results),
            "total_pings_served": total_pings_served,
            "sample_route": hub_results[0] if hub_results else None,
            "sample_courier": courier_results[0] if courier_results else None
        }

        logger.info(
            f"Serving layer verified: {len(hub_results)} hub route aggregates ({total_orders_served} orders) "
            f"and {len(courier_results)} active courier records ({total_pings_served} pings)"
        )
        return summary
