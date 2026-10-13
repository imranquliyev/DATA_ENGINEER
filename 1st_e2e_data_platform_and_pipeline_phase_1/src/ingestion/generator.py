import hashlib
import random
from datetime import datetime, time
from typing import Dict, List, Optional
from src.common.logger import get_logger

logger = get_logger("ingestion_generator")

HUBS = ["HUB-BAKU-NORTH", "HUB-BAKU-CENTER", "HUB-BAKU-SOUTH", "HUB-SUMGAYIT", "HUB-GANJA"]
COURIERS = ["C-101", "C-102", "C-103", "C-104"]
STATUSES = ["CREATED", "DISPATCHED", "IN_TRANSIT", "DELIVERED", "FAILED_ATTEMPT"]


class LogisticsDataGenerator:
    """
    Realistic synthetic logistics event generator parameterized by logical date.
    Injects realistic telemetry jitter, GPS noise, and dirty records for quality validation.
    """

    def __init__(self, dirty_rate: float = 0.05, seed: Optional[int] = None):
        self.dirty_rate = dirty_rate
        self.fixed_seed = seed

    def _seed_for_date(self, logical_date: str, salt: int = 0):
        if self.fixed_seed is not None:
            random.seed(self.fixed_seed + salt)
        else:
            seed_val = int(hashlib.md5(f"{logical_date}_{salt}".encode("utf-8")).hexdigest()[:8], 16)
            random.seed(seed_val)

    def generate_orders(self, count: int = 1200, logical_date: str = "2026-10-13") -> List[Dict]:
        """
        Generates synthetic package orders for a designated logical date.
        Guarantees non-trivial volume (>= 1000 rows).
        """
        self._seed_for_date(logical_date, salt=1)
        orders = []
        target_date = datetime.strptime(logical_date, "%Y-%m-%d").date()

        for i in range(count):
            is_dirty = random.random() < self.dirty_rate
            order_id = f"ORD-{logical_date.replace('-', '')}-{i+1:05d}"
            origin = random.choice(HUBS)
            dest = random.choice([h for h in HUBS if h != origin])

            # Spread timestamps across the logical date
            hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            created_dt = datetime.combine(target_date, time(hour, minute, second))

            promised_hours = random.choice([12, 24, 48])
            weight = round(random.uniform(0.5, 30.0), 2)

            # Simulated actual hours for SLA evaluation
            # 85% arrive on time, 15% breach SLA
            sla_breach = random.random() < 0.15
            if sla_breach:
                actual_hours = round(promised_hours + random.uniform(2.0, 20.0), 2)
            else:
                actual_hours = round(random.uniform(2.0, promised_hours * 0.9), 2)

            # Dirty data injection
            if is_dirty and random.random() > 0.5:
                customer_id = None
            else:
                customer_id = f"CUST-{random.randint(1000, 9999)}"

            if is_dirty and random.random() > 0.5:
                status = "CORRUPT_STATUS"
            else:
                status = random.choice(STATUSES)

            orders.append({
                "order_id": order_id,
                "tracking_number": f"TRK-{logical_date.replace('-', '')}-{random.randint(100000, 999999)}",
                "customer_id": customer_id,
                "origin_hub": origin,
                "dest_hub": dest,
                "package_weight_kg": weight,
                "promised_hours": promised_hours,
                "actual_hours": actual_hours,
                "status": status,
                "created_at": created_dt.isoformat(),
                "batch_date": logical_date
            })

        logger.info(
            f"Generated {len(orders)} synthetic orders for logical_date={logical_date} (dirty_rate={self.dirty_rate})"
        )
        return orders

    def generate_telemetry(self, count: int = 2500, logical_date: str = "2026-10-13") -> List[Dict]:
        """
        Generates synthetic courier GPS telemetry pings for a designated logical date.
        """
        self._seed_for_date(logical_date, salt=2)
        pings = []
        target_date = datetime.strptime(logical_date, "%Y-%m-%d").date()
        base_lat, base_lon = 40.409264, 49.867092  # Baku coordinates

        for i in range(count):
            is_dirty = random.random() < self.dirty_rate
            ping_id = f"PNG-{logical_date.replace('-', '')}-{i+1:05d}"
            courier = random.choice(COURIERS)

            # Spread timestamps across the day
            hour = random.randint(6, 22)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            recorded_dt = datetime.combine(target_date, time(hour, minute, second))

            if is_dirty:
                lat = 0.0 if random.random() > 0.5 else 999.99
                lon = 0.0 if random.random() > 0.5 else -999.99
                speed = -45.0
            else:
                lat = round(base_lat + random.uniform(-0.15, 0.15), 6)
                lon = round(base_lon + random.uniform(-0.15, 0.15), 6)
                speed = round(random.uniform(0.0, 75.0), 1)

            battery = random.randint(15, 100)

            pings.append({
                "ping_id": ping_id,
                "courier_id": courier,
                "latitude": lat,
                "longitude": lon,
                "speed_kmh": speed,
                "battery_pct": battery,
                "recorded_at": recorded_dt.isoformat(),
                "batch_date": logical_date
            })

        logger.info(
            f"Generated {len(pings)} synthetic telemetry pings for logical_date={logical_date} (dirty_rate={self.dirty_rate})"
        )
        return pings
