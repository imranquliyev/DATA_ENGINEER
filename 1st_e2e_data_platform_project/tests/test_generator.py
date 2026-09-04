from src.ingestion.generator import LogisticsDataGenerator


def test_generator_order_creation():
    generator = LogisticsDataGenerator(dirty_rate=0.0)
    orders = generator.generate_orders(count=20)
    assert len(orders) == 20
    assert "order_id" in orders[0]
    assert orders[0]["order_id"].startswith("ORD-")


def test_generator_telemetry_creation():
    generator = LogisticsDataGenerator(dirty_rate=0.0)
    pings = generator.generate_telemetry(count=50)
    assert len(pings) == 50
    assert "ping_id" in pings[0]
    assert pings[0]["ping_id"].startswith("PNG-")
    assert 40.0 <= pings[0]["latitude"] <= 41.0
