import os
import sys
import uuid
from datetime import datetime, timedelta

# Ensure /opt/airflow is in python path
sys.path.insert(0, "/opt/airflow")

from airflow import DAG
from airflow.operators.python import PythonOperator

# Import platform modules
from src.ingestion.generator import LogisticsDataGenerator
from src.ingestion.s3_uploader import MinIOUploader
from src.quality.checks import DataQualityValidator
from src.transformation.loader import PipelineLoader

default_args = {
    'owner': 'fastroute_data_team',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=1),
}


def task_generate_and_upload_raw(**kwargs):
    """Generates synthetic logistics events and uploads to MinIO S3 raw bucket."""
    generator = LogisticsDataGenerator(dirty_rate=0.08)
    orders = generator.generate_orders(count=150)
    pings = generator.generate_telemetry(count=500)

    uploader = MinIOUploader()
    orders_s3 = uploader.upload_batch("orders", orders)
    pings_s3 = uploader.upload_batch("telemetry", pings)

    batch_id = f"BATCH-{uuid.uuid4().hex[:8].upper()}"
    return {
        "batch_id": batch_id,
        "orders": orders,
        "pings": pings,
        "orders_s3": orders_s3,
        "pings_s3": pings_s3
    }


def task_run_quality_checks(**kwargs):
    """Performs data quality checks and logs audit records to PostgreSQL."""
    ti = kwargs['ti']
    payload = ti.xcom_pull(task_ids='generate_and_upload_raw')
    batch_id = payload['batch_id']

    valid_orders, invalid_orders, order_metrics = DataQualityValidator.validate_orders_batch(payload['orders'])
    valid_pings, invalid_pings, ping_metrics = DataQualityValidator.validate_telemetry_batch(payload['pings'])

    DataQualityValidator.log_audit_to_postgres(batch_id, "orders", order_metrics)
    DataQualityValidator.log_audit_to_postgres(batch_id, "telemetry", ping_metrics)

    return {
        "batch_id": batch_id,
        "valid_orders": valid_orders,
        "valid_pings": valid_pings
    }


def task_load_staging_and_olap(**kwargs):
    """Loads validated records into PostgreSQL staging and ClickHouse OLAP tables."""
    ti = kwargs['ti']
    payload = ti.xcom_pull(task_ids='run_quality_checks')

    PipelineLoader.load_orders_to_postgres(payload['valid_orders'])
    PipelineLoader.load_telemetry_to_clickhouse(payload['valid_pings'])


with DAG(
    'fastroute_logistics_pipeline',
    default_args=default_args,
    description='End-to-end logistics SLA and telemetry ingestion pipeline',
    schedule_interval='@hourly',
    catchup=False,
    tags=['logistics', 'sla', 'clickhouse', 'minio']
) as dag:

    t1 = PythonOperator(
        task_id='generate_and_upload_raw',
        python_callable=task_generate_and_upload_raw
    )

    t2 = PythonOperator(
        task_id='run_quality_checks',
        python_callable=task_run_quality_checks
    )

    t3 = PythonOperator(
        task_id='load_staging_and_olap',
        python_callable=task_load_staging_and_olap
    )

    t1 >> t2 >> t3
