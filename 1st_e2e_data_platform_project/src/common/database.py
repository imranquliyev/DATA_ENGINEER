import boto3
import psycopg2
import clickhouse_connect
from src.common.config import get_settings
from src.common.logger import get_logger

logger = get_logger("database_common")


def _resolve_host(configured_host: str) -> str:
    """Tries resolving container hostname; falls back to localhost if running outside docker."""
    try:
        import socket
        socket.gethostbyname(configured_host)
        return configured_host
    except Exception:
        return "localhost"


def get_postgres_connection():
    """Returns a connection to PostgreSQL staging database."""
    settings = get_settings()
    host = _resolve_host(settings.postgres_host)
    return psycopg2.connect(
        host=host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        dbname=settings.postgres_db
    )


def get_clickhouse_client():
    """Returns a ClickHouse connect client."""
    settings = get_settings()
    host = _resolve_host(settings.clickhouse_host)
    return clickhouse_connect.get_client(
        host=host,
        port=settings.clickhouse_http_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_db
    )


def get_minio_client():
    """Returns boto3 S3 client configured for MinIO."""
    settings = get_settings()
    host = _resolve_host(settings.minio_host)
    return boto3.client(
        's3',
        endpoint_url=f"http://{host}:{settings.minio_port}",
        aws_access_key_id=settings.minio_root_user,
        aws_secret_access_key=settings.minio_root_password,
        region_name='us-east-1'
    )


def check_infrastructure_health() -> dict:
    """Pings all database and storage services and returns status map."""
    settings = get_settings()
    health = {
        "postgres": False,
        "minio": False,
        "clickhouse": False
    }

    # PostgreSQL check
    try:
        conn = get_postgres_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
        conn.close()
        health["postgres"] = True
    except Exception as e:
        logger.warning(f"PostgreSQL health check failed: {e}")

    # MinIO check
    try:
        s3 = get_minio_client()
        s3.list_buckets()
        health["minio"] = True
    except Exception as e:
        logger.warning(f"MinIO health check failed: {e}")

    # ClickHouse check
    try:
        ch = get_clickhouse_client()
        ch.command("SELECT 1")
        health["clickhouse"] = True
    except Exception as e:
        logger.warning(f"ClickHouse health check failed: {e}")

    return health
