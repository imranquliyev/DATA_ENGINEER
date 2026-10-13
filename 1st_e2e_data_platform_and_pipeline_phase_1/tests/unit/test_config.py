from src.common.config import get_settings


def test_settings_default_values():
    settings = get_settings()
    assert settings.postgres_port == 5432
    assert settings.minio_port == 9000
    assert settings.clickhouse_http_port == 8123
    assert settings.minio_raw_bucket == "fastroute-raw"
    assert settings.batch_order_count >= 1000
    assert settings.batch_telemetry_count >= 1000
    assert settings.fail_ingestion is False
