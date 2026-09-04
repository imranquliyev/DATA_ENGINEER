from src.quality.checks import DataQualityValidator


def test_telemetry_quality_validation():
    sample_pings = [
        {"ping_id": "P1", "latitude": 40.40, "longitude": 49.86, "speed_kmh": 35.0},
        {"ping_id": "P2", "latitude": 0.0, "longitude": 0.0, "speed_kmh": -10.0}  # Invalid
    ]

    valid, invalid, metrics = DataQualityValidator.validate_telemetry_batch(sample_pings)
    assert len(valid) == 1
    assert len(invalid) == 1
    assert metrics["passed"] == 1
    assert metrics["failed"] == 1
    assert invalid[0]["ping_id"] == "P2"


def test_orders_quality_validation():
    sample_orders = [
        {"order_id": "O1", "tracking_number": "T1", "status": "CREATED"},
        {"order_id": "O2", "tracking_number": "T2", "status": "INVALID_ENUM"}  # Invalid
    ]

    valid, invalid, metrics = DataQualityValidator.validate_orders_batch(sample_orders)
    assert len(valid) == 1
    assert len(invalid) == 1
    assert invalid[0]["order_id"] == "O2"
