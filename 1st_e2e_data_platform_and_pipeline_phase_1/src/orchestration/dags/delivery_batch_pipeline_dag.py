import os
import sys
from datetime import datetime, timedelta

# Ensure project modules are discoverable in Airflow
for path in ["/opt/airflow", "/opt/airflow/src"]:
    if path not in sys.path:
        sys.path.insert(0, path)

from airflow import DAG
from airflow.operators.python import PythonOperator

from src.orchestration.tasks import (
    task_ingest_source,
    task_raw_storage_landing,
    task_load_staging,
    task_transform_curated,
    task_run_quality_checks,
    task_publish_serving
)

default_args = {
    'owner': 'fastroute_data_team',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(seconds=10),
}


def _get_logical_date(**kwargs) -> str:
    """Extracts logical date parameter from DAG run conf or fallback to execution ds."""
    dag_run = kwargs.get('dag_run')
    if dag_run and dag_run.conf and 'logical_date' in dag_run.conf:
        return str(dag_run.conf['logical_date'])
    return str(kwargs.get('ds', datetime.utcnow().strftime('%Y-%m-%d')))


def _check_fail_switch(**kwargs) -> bool:
    """Checks if deliberate failure switch is enabled via conf or environment."""
    dag_run = kwargs.get('dag_run')
    if dag_run and dag_run.conf and dag_run.conf.get('fail_ingestion'):
        return True
    return os.getenv("FAIL_INGESTION", "false").lower() in ("true", "1")


def airflow_ingest_source(**kwargs):
    logical_date = _get_logical_date(**kwargs)
    fail_deliberately = _check_fail_switch(**kwargs)
    result = task_ingest_source(logical_date=logical_date, fail_deliberately=fail_deliberately)
    return {
        "logical_date": logical_date,
        "rows_extracted": result["rows_extracted"]
    }


def airflow_raw_landing(**kwargs):
    logical_date = _get_logical_date(**kwargs)
    result = task_raw_storage_landing(logical_date=logical_date)
    return result


def airflow_load_staging(**kwargs):
    logical_date = _get_logical_date(**kwargs)
    result = task_load_staging(logical_date=logical_date)
    return result


def airflow_transform_curated(**kwargs):
    logical_date = _get_logical_date(**kwargs)
    result = task_transform_curated(logical_date=logical_date)
    return result


def airflow_quality_checks(**kwargs):
    logical_date = _get_logical_date(**kwargs)
    result = task_run_quality_checks(logical_date=logical_date)
    return result


def airflow_publish_serving(**kwargs):
    logical_date = _get_logical_date(**kwargs)
    result = task_publish_serving(logical_date=logical_date)
    return result


with DAG(
    dag_id='fastroute_batch_pipeline',
    default_args=default_args,
    description='Phase 1 Walking Skeleton: End-to-End Batch Pipeline (Source -> MinIO -> Staging -> ClickHouse -> Serving)',
    schedule_interval='@daily',
    catchup=False,
    is_paused_upon_creation=False,
    tags=['phase-1', 'batch', 'minio', 'postgres', 'clickhouse', 'logistics']
) as dag:

    # Stage 1: Ingestion (Configured with retries & deliberate failure switch)
    stage_1_ingest = PythonOperator(
        task_id='1_ingest_source',
        python_callable=airflow_ingest_source,
        retries=2,
        retry_delay=timedelta(seconds=15)
    )

    # Stage 2: Raw Landing
    stage_2_raw = PythonOperator(
        task_id='2_raw_storage_landing',
        python_callable=airflow_raw_landing
    )

    # Stage 3: Operational Staging Load
    stage_3_staging = PythonOperator(
        task_id='3_load_staging',
        python_callable=airflow_load_staging
    )

    # Stage 4: Curated Warehouse Materialization
    stage_4_curated = PythonOperator(
        task_id='4_transform_curated',
        python_callable=airflow_transform_curated
    )

    # Stage 5: Data Quality Gate (Failure stops pipeline)
    stage_5_quality = PythonOperator(
        task_id='5_run_quality_checks',
        python_callable=airflow_quality_checks
    )

    # Stage 6: Serving & Consumption Publication
    stage_6_serving = PythonOperator(
        task_id='6_publish_serving',
        python_callable=airflow_publish_serving
    )

    # Explicit linear dependencies across every architecture hop
    stage_1_ingest >> stage_2_raw >> stage_3_staging >> stage_4_curated >> stage_5_quality >> stage_6_serving
