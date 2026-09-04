import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from src.common.logger import get_logger

logger = get_logger("generator")

HUBS = ["HUB-BAKU-NORTH", "HUB-BAKU-CENTER", "HUB-BAKU-SOUTH", "HUB-SUMGAYIT", "HUB-GANJA"]
COURIERS = ["C-101", "C-102", "C-103", "C-104"]
STATUSES = ["CREATED", "DISPATCHED", "IN_TRANSIT", "DELIVERED", "FAILED_ATTEMPT"]


class LogisticsDataGenerator:
    """Generates synthetic logistics events with configurable dirty record injection."""

    def __init__(self, dirty_rate: float = 0.05):
        self.dirty_rate = dirty_rate

    def generate_orders(self, count: int = 100) -> List[Dict]:
        """Generates synthetic package orders."""
        orders = []
        now = datetime.utcnow()

        for _ in range(count):
            is_dirty = random.random() < self.dirty_rate
            order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
            origin = random.choice(HUBS)
            dest = random.choice([h for h in HUBS if h != origin])
            
            created = now - timedelta(hours=random.randint(1, 48))
            promised_hours = random.choice([12, 24, 48])
            weight = round(random.uniform(0.5, 25.0), 2)
            
            # Inject dirty fields if specified
            customer_id = None if is_dirty else f"CUST-{random.randint(1000, 9999)}"
            status = "INVALID_ENUM" if is_dirty and random.random() > 0.5 else random.choice(STATUSES)
            
            orders.append({
                "order_id": order_id,
                "tracking_number": f"TRK-{random.randint(10000000, 99999999)}",
                "customer_id": customer_id,
                "origin_hub": origin,
                "dest_hub": dest,
                "package_weight_kg": weight,
                "promised_hours": promised_hours,
                "status": status,
                "created_at": created.isoformat()
            })

        logger.info(f"Generated {len(orders)} synthetic orders (dirty rate: {self.dirty_rate})")
        return orders

    def generate_telemetry(self, count: int = 500) -> List[Dict]:
        """Generates synthetic courier GPS telemetry pings."""
        pings = []
        now = datetime.utcnow()
        # Baku bounding coordinates: Lat ~ 40.40, Lon ~ 49.86
        base_lat, base_lon = 40.409264, 49.867092

        for i in range(count):
            is_dirty = random.random() < self.dirty_rate
            ping_id = f"PNG-{uuid.uuid4().hex[:8].upper()}"
            courier = random.choice(COURIERS)
            
            if is_dirty:
                # Inject corrupted GPS coordinates (0.0 or off-grid)
                lat = 0.0 if random.random() > 0.5 else 999.99
                lon = 0.0 if random.random() > 0.5 else -999.99
                speed = -50.0  # Invalid speed
            else:
                lat = round(base_lat + random.uniform(-0.15, 0.15), 6)
                lon = round(base_lon + random.uniform(-0.15, 0.15), 6)
                speed = round(random.uniform(0.0, 75.0), 1)

            recorded_at = (now - timedelta(seconds=i * 5)).isoformat()
            battery = random.randint(10, 100)

            pings.append({
                "ping_id": ping_id,
                "courier_id": courier,
                "latitude": lat,
                "longitude": lon,
                "speed_kmh": speed,
                "battery_pct": battery,
                "recorded_at": recorded_at
            })

        logger.info(f"Generated {len(pings)} synthetic telemetry pings (dirty rate: {self.dirty_rate})")
        return pings
