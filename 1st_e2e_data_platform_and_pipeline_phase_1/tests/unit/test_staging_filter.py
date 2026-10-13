from src.staging.loader import StagingLoader


def test_staging_filter_orders():
    loader = StagingLoader()
    sample_orders = [
        {"order_id": "ORD-1", "tracking_number": "TRK-1", "status": "CREATED"},
        {"order_id": "ORD-2", "tracking_number": "TRK-2", "status": "CORRUPT_STATUS"},  # invalid
        {"order_id": "", "tracking_number": "TRK-3", "status": "CREATED"},                # missing id
    ]

    valid, quarantined = loader.filter_orders(sample_orders)
    assert len(valid) == 1
    assert len(quarantined) == 2
    assert valid[0]["order_id"] == "ORD-1"


def test_staging_filter_telemetry():
    loader = StagingLoader()
    sample_pings = [
        {"ping_id": "P1", "latitude": 40.40, "longitude": 49.86, "speed_kmh": 35.0},
        {"ping_id": "P2", "latitude": 0.0, "longitude": 0.0, "speed_kmh": 10.0},       # invalid (0,0)
        {"ping_id": "P3", "latitude": 40.40, "longitude": 49.86, "speed_kmh": -5.0},    # negative speed
    ]

    valid, quarantined = loader.filter_telemetry(sample_pings)
    assert len(valid) == 1
    assert len(quarantined) == 2
    assert valid[0]["ping_id"] == "P1"
