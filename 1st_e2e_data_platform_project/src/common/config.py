import os
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central Application Configuration using Pydantic Settings."""

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # PostgreSQL
    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_user: str = Field(default="fastroute_user", alias="POSTGRES_USER")
    postgres_password: str = Field(default="fastroute_password", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="fastroute_db", alias="POSTGRES_DB")

    # MinIO
    minio_host: str = Field(default="minio", alias="MINIO_HOST")
    minio_port: int = Field(default=9000, alias="MINIO_PORT")
    minio_root_user: str = Field(default="minioadmin", alias="MINIO_ROOT_USER")
    minio_root_password: str = Field(default="minioadmin", alias="MINIO_ROOT_PASSWORD")
    minio_raw_bucket: str = Field(default="fastroute-raw", alias="MINIO_RAW_BUCKET")
    minio_staging_bucket: str = Field(default="fastroute-staging", alias="MINIO_STAGING_BUCKET")

    # ClickHouse
    clickhouse_host: str = Field(default="clickhouse", alias="CLICKHOUSE_HOST")
    clickhouse_http_port: int = Field(default=8123, alias="CLICKHOUSE_HTTP_PORT")
    clickhouse_user: str = Field(default="default", alias="CLICKHOUSE_USER")
    clickhouse_password: str = Field(default="clickhouse_secret", alias="CLICKHOUSE_PASSWORD")
    clickhouse_db: str = Field(default="fastroute_analytics", alias="CLICKHOUSE_DB")

    # Airflow
    airflow_host: str = Field(default="airflow-webserver", alias="AIRFLOW_HOST")
    airflow_port: int = Field(default=8080, alias="AIRFLOW_WWW_PORT")
    airflow_user: str = Field(default="airflow", alias="AIRFLOW_ADMIN_USER")
    airflow_password: str = Field(default="airflow", alias="AIRFLOW_ADMIN_PASSWORD")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def get_settings() -> Settings:
    return Settings()
