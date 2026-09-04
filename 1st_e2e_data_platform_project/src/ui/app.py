import os
import sys
import uuid
import pandas as pd
import plotly.express as px
import streamlit as st

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.common.config import get_settings
from src.common.database import (
    check_infrastructure_health,
    get_postgres_connection,
    get_clickhouse_client,
    get_minio_client
)
from src.ingestion.generator import LogisticsDataGenerator
from src.ingestion.s3_uploader import MinIOUploader
from src.quality.checks import DataQualityValidator
from src.transformation.loader import PipelineLoader

st.set_page_config(
    page_title="FastRoute Logistics — Data Platform Control Center",
    page_icon="🚚",
    layout="wide"
)

st.title("🚚 FastRoute Logistics — Data Platform Control Center")
st.caption("End-to-End Data Engineering Platform for Route SLA & Courier Telemetry Analytics")

# --- Sidebar & Navigation ---
st.sidebar.header("🛠️ Platform Navigation")
navigation = st.sidebar.radio(
    "Select Module",
    [
        "System Health & Status",
        "Interactive Data Generator",
        "Data Explorer (MinIO / Postgres / ClickHouse)",
        "SLA & Fleet Analytics",
        "Project Plan & Architecture"
    ]
)

settings = get_settings()

# --- Module 1: System Health ---
if navigation == "System Health & Status":
    st.header("⚡ System Infrastructure Health")
    st.write("Live status check of declared Docker services and databases:")

    if st.button("🔄 Refresh Health Check"):
        st.rerun()

    health = check_infrastructure_health()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if health["postgres"]:
            st.success("PostgreSQL Staging DB\n\n🟢 Connected (5432)")
        else:
            st.error("PostgreSQL Staging DB\n\n🔴 Offline / Unreachable")

    with col2:
        if health["minio"]:
            st.success("MinIO S3 Object Storage\n\n🟢 Connected (9000)")
        else:
            st.error("MinIO S3 Object Storage\n\n🔴 Offline / Unreachable")

    with col3:
        if health["clickhouse"]:
            st.success("ClickHouse OLAP Engine\n\n🟢 Connected (8123)")
        else:
            st.error("ClickHouse OLAP Engine\n\n🔴 Offline / Unreachable")

    with col4:
        st.info("Apache Airflow\n\n🔵 Webserver Port 8080")

    st.markdown("---")
    st.subheader("📌 Service Port Directory")
    st.table(pd.DataFrame([
        {"Service": "Streamlit Control Center", "URL / Port": "http://localhost:8501", "Purpose": "Interactive test UI"},
        {"Service": "Apache Airflow DAG UI", "URL / Port": "http://localhost:8080", "Purpose": "Pipeline scheduler & DAG runner"},
        {"Service": "MinIO S3 Console", "URL / Port": "http://localhost:9001", "Purpose": "Raw S3 file browser"},
        {"Service": "ClickHouse HTTP API", "URL / Port": "http://localhost:8123", "Purpose": "Columnar OLAP query endpoint"},
        {"Service": "PostgreSQL Staging", "URL / Port": "localhost:5432", "Purpose": "Relational staging & metadata store"}
    ]))

# --- Module 2: Data Generator ---
elif navigation == "Interactive Data Generator":
    st.header("🎲 Interactive Synthetic Data Generator")
    st.write("Generate realistic logistics packages and GPS telemetry events with optional dirty records injection.")

    col_a, col_b = st.columns(2)
    with col_a:
        order_count = st.slider("Package Orders to Generate", 10, 500, 100)
        telemetry_count = st.slider("Telemetry Pings to Generate", 50, 2000, 500)
    with col_b:
        dirty_rate = st.slider("Dirty / Corrupted Record Injection Rate (%)", 0.0, 30.0, 5.0) / 100.0

    if st.button("🚀 Trigger Ingestion & Pipeline Run"):
        with st.spinner("Generating events, uploading to MinIO, validating, and loading..."):
            generator = LogisticsDataGenerator(dirty_rate=dirty_rate)
            orders = generator.generate_orders(count=order_count)
            pings = generator.generate_telemetry(count=telemetry_count)

            st.subheader("1. Ingestion — Raw Data Samples")
            st.json({"sample_order": orders[0], "sample_telemetry": pings[0]})

            # Upload to MinIO
            uploader = MinIOUploader()
            try:
                orders_s3 = uploader.upload_batch("orders", orders)
                pings_s3 = uploader.upload_batch("telemetry", pings)
                st.success(f"Uploaded raw JSON files to MinIO S3: `{orders_s3}`")
            except Exception as e:
                st.warning(f"Could not upload to MinIO S3 (service offline?): {e}")

            # Quality validation
            st.subheader("2. Data Quality Enforcement")
            valid_orders, invalid_orders, order_metrics = DataQualityValidator.validate_orders_batch(orders)
            valid_pings, invalid_pings, ping_metrics = DataQualityValidator.validate_telemetry_batch(pings)

            col_q1, col_q2 = st.columns(2)
            col_q1.metric("Valid Orders", f"{order_metrics['passed']}/{order_metrics['total']}")
            col_q2.metric("Valid Telemetry Pings", f"{ping_metrics['passed']}/{ping_metrics['total']}")

            # Log audit
            batch_id = f"UI-BATCH-{uuid.uuid4().hex[:6].upper()}"
            DataQualityValidator.log_audit_to_postgres(batch_id, "orders", order_metrics)
            DataQualityValidator.log_audit_to_postgres(batch_id, "telemetry", ping_metrics)

            # Load DBs
            st.subheader("3. Loading Staging & ClickHouse OLAP")
            try:
                PipelineLoader.load_orders_to_postgres(valid_orders)
                PipelineLoader.load_telemetry_to_clickhouse(valid_pings)
                st.success("Successfully loaded valid records into PostgreSQL Staging & ClickHouse OLAP!")
            except Exception as e:
                st.warning(f"DB load encountered warning: {e}")

# --- Module 3: Data Explorer ---
elif navigation == "Data Explorer (MinIO / Postgres / ClickHouse)":
    st.header("🔍 Storage & Warehouse Data Explorer")
    tab1, tab2, tab3 = st.tabs(["🪣 MinIO S3 Raw Lake", "🐘 PostgreSQL Staging DB", "⚡ ClickHouse OLAP Engine"])

    with tab1:
        st.subheader("MinIO Raw Buckets File Listing")
        try:
            s3 = get_minio_client()
            buckets = s3.list_buckets().get("Buckets", [])
            st.write(f"Buckets found: `{[b['Name'] for b in buckets]}`")

            response = s3.list_objects_v2(Bucket=settings.minio_raw_bucket)
            objects = response.get("Contents", [])
            if objects:
                file_df = pd.DataFrame(objects)[["Key", "LastModified", "Size"]]
                st.dataframe(file_df, use_container_width=True)
            else:
                st.info("No raw JSON/Parquet files found in MinIO raw bucket yet. Use the Data Generator tab to create batches.")
        except Exception as e:
            st.error(f"Could not connect to MinIO S3: {e}")

    with tab2:
        st.subheader("PostgreSQL Staging Tables")
        try:
            conn = get_postgres_connection()
            orders_df = pd.read_sql("SELECT * FROM staging.staging_orders ORDER BY created_at DESC LIMIT 50;", conn)
            audit_df = pd.read_sql("SELECT * FROM audit.quality_audit_logs ORDER BY checked_at DESC LIMIT 50;", conn)
            conn.close()

            st.markdown("#### `staging.staging_orders` (Latest 50)")
            st.dataframe(orders_df, use_container_width=True)

            st.markdown("#### `audit.quality_audit_logs` (Quarantine Audit History)")
            st.dataframe(audit_df, use_container_width=True)
        except Exception as e:
            st.error(f"Could not query PostgreSQL staging DB: {e}")

    with tab3:
        st.subheader("ClickHouse OLAP Analytics Tables")
        try:
            ch = get_clickhouse_client()
            telemetry_df = ch.query_df("SELECT * FROM fact_telemetry_pings ORDER BY recorded_at DESC LIMIT 100")
            couriers_df = ch.query_df("SELECT * FROM dim_couriers")

            st.markdown("#### `fact_telemetry_pings` (Latest 100 ClickHouse Rows)")
            st.dataframe(telemetry_df, use_container_width=True)

            st.markdown("#### `dim_couriers` Dimension Table")
            st.dataframe(couriers_df, use_container_width=True)
        except Exception as e:
            st.error(f"Could not query ClickHouse engine: {e}")

# --- Module 4: SLA Analytics ---
elif navigation == "SLA & Fleet Analytics":
    st.header("📊 Delivery SLA & Courier Telemetry Analytics")

    try:
        ch = get_clickhouse_client()
        telemetry_df = ch.query_df("SELECT * FROM fact_telemetry_pings LIMIT 1000")

        if not telemetry_df.empty:
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Total Telemetry Rows", len(telemetry_df))
            col_m2.metric("Avg Driver Speed (km/h)", f"{telemetry_df['speed_kmh'].mean():.1f}")
            col_m3.metric("Avg Battery Level (%)", f"{telemetry_df['battery_pct'].mean():.1f}%")

            st.subheader("Courier Telemetry Scatter (Speed vs Battery)")
            fig = px.scatter(
                telemetry_df,
                x="speed_kmh",
                y="battery_pct",
                color="courier_id",
                hover_data=["latitude", "longitude"],
                title="GPS Ping Telemetry Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No ClickHouse data available yet. Please use the Data Generator tab to create sample batches!")
    except Exception as e:
        st.warning(f"Analytics query status: {e}")

# --- Module 5: Docs Viewer ---
elif navigation == "Project Plan & Architecture":
    st.header("📄 Project Plan & Architecture Documentation")
    doc_choice = st.radio("View Document", ["docs/PROJECT_PLAN.md", "README.md"])
    
    file_path = os.path.join(os.path.dirname(__file__), "../..", doc_choice)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f.read())
    else:
        st.error(f"Document file {doc_choice} not found.")
