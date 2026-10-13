from src.ingestion.generator import LogisticsDataGenerator


def test_generator_order_volume_and_attributes():
    generator = LogisticsDataGenerator(dirty_rate=0.0)
    orders = generator.generate_orders(count=1200, logical_date="2026-10-13")
    assert len(orders) == 1200
    assert orders[0]["order_id"].startswith("ORD-20261013-")
    assert orders[0]["batch_date"] == "2026-10-13"
    assert "tracking_number" in orders[0]
    assert "promised_hours" in orders[0]


def test_generator_telemetry_volume_and_coordinates():
    generator = LogisticsDataGenerator(dirty_rate=0.0)
    pings = generator.generate_telemetry(count=2500, logical_date="2026-10-13")
    assert len(pings) == 2500
    assert pings[0]["ping_id"].startswith("PNG-20261013-")
    assert pings[0]["batch_date"] == "2026-10-13"
    assert 40.0 <= pings[0]["latitude"] <= 41.0
    assert 49.0 <= pings[0]["longitude"] <= 50.5
    assert pings[0]["speed_kmh"] >= 0.0


def test_generator_dirty_records_injection():
    generator = LogisticsDataGenerator(dirty_rate=0.5, seed=42)
    orders = generator.generate_orders(count=200, logical_date="2026-10-13")
    pings = generator.generate_telemetry(count=200, logical_date="2026-10-13")

    has_corrupt_status = any(o["status"] == "CORRUPT_STATUS" for o in orders)
    has_null_cust = any(o["customer_id"] is None for o in orders)
    has_corrupt_gps = any(p["latitude"] == 0.0 or p["latitude"] == 999.99 for p in pings)

    assert has_corrupt_status or has_null_cust
    assert has_corrupt_gps
