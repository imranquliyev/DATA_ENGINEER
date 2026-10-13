import os
import sys
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.common.config import get_settings
from src.common.database import (
    check_infrastructure_health,
    get_postgres_connection,
    get_clickhouse_client,
    get_minio_client
)
from src.orchestration.runner import run_pipeline

st.set_page_config(
    page_title="FastRoute Logistics — Data Platform Control Center",
    page_icon="🚚",
    layout="wide"
)

st.title("🚚 FastRoute Logistics — Data Platform Control Center")
st.caption("Phase 1 Walking Skeleton: End-to-End Orchestrated Batch Pipeline")

# --- Sidebar & Navigation ---
st.sidebar.header("🛠️ Platform Navigation")
navigation = st.sidebar.radio(
    "Select Module",
    [
        "System Health & Status",
        "Pipeline Execution & Control",
        "Data Layer Explorer (All Hops)",
        "Serving & SLA Analytics",
        "Documentation & Architecture"
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
            st.success("PostgreSQL Staging DB\n\n🟢 Connected (:5432)")
        else:
            st.error("PostgreSQL Staging DB\n\n🔴 Offline / Unreachable")

    with col2:
        if health["minio"]:
            st.success("MinIO S3 Object Storage\n\n🟢 Connected (:9000)")
        else:
            st.error("MinIO S3 Object Storage\n\n🔴 Offline / Unreachable")

    with col3:
        if health["clickhouse"]:
            st.success("ClickHouse OLAP Engine\n\n🟢 Connected (:8123)")
        else:
            st.error("ClickHouse OLAP Engine\n\n🔴 Offline / Unreachable")

    with col4:
        st.info("Apache Airflow 2.8\n\n🔵 Webserver Port :8080")

    st.markdown("---")
    st.subheader("📌 Service Port Directory & Endpoints")
    st.table(pd.DataFrame([
        {"Service": "Streamlit Control Center", "URL / Port": "http://localhost:8501", "Purpose": "Interactive management UI"},
        {"Service": "Apache Airflow DAG UI", "URL / Port": "http://localhost:8080", "Purpose": "DAG orchestration & scheduling"},
        {"Service": "MinIO S3 Console", "URL / Port": "http://localhost:9001", "Purpose": "Raw S3 file browser"},
        {"Service": "ClickHouse HTTP API", "URL / Port": "http://localhost:8123", "Purpose": "Columnar OLAP query endpoint"},
        {"Service": "PostgreSQL Staging", "URL / Port": "localhost:5432", "Purpose": "Relational staging & audit logging"}
    ]))

# --- Module 2: Pipeline Control ---
elif navigation == "Pipeline Execution & Control":
    st.header("🚀 Pipeline Execution & Deliberate Failure Switch")
    st.write(
        "Trigger the complete 6-stage end-to-end batch pipeline for a specified logical date, "
        "or test the deliberate failure switch."
    )

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        selected_date = st.date_input("Logical Batch Date", datetime(2026, 10, 13))
        logical_date_str = selected_date.strftime("%Y-%m-%d")

    with col_p2:
        fail_switch = st.checkbox("💥 Activate Deliberate Failure Switch (FAIL_INGESTION)", value=False)
        if fail_switch:
            st.warning("Deliberate failure is ACTIVE: Ingestion task will fail and downstream stages will halt.")

    if st.button("▶️ Execute Batch Pipeline"):
        progress_bar = st.progress(0)
        status_box = st.empty()

        status_box.info("Initiating 6-stage batch pipeline...")
        progress_bar.progress(15)

        success = run_pipeline(logical_date=logical_date_str, fail_ingestion=fail_switch)

        if success:
            progress_bar.progress(100)
            status_box.success(
                f"✅ Pipeline completed successfully for logical_date={logical_date_str}! "
                f"Check the 'Data Layer Explorer' or 'Serving & SLA Analytics' tabs."
            )
        else:
            progress_bar.progress(20)
            status_box.error(
                "❌ Pipeline failed as expected (deliberate failure or service offline). "
                "Downstream tasks halted and run marked as failed."
            )

# --- Module 3: Data Layer Explorer ---
elif navigation == "Data Layer Explorer (All Hops)":
    st.header("🔍 Architecture Hop & Data Layer Explorer")
    hop_tab1, hop_tab2, hop_tab3, hop_tab4 = st.tabs([
        "🪣 Hop 1: MinIO Raw Lake",
        "🐘 Hop 2: PostgreSQL Staging",
        "⚡ Hop 3: ClickHouse Curated OLAP",
        "📊 Hop 4: Serving Layer Views"
    ])

    with hop_tab1:
        st.subheader("Raw Layer: MinIO S3 Object Storage")
        try:
            s3 = get_minio_client()
            buckets = s3.list_buckets().get("Buckets", [])
            st.write(f"Available Buckets: `{[b['Name'] for b in buckets]}`")

            response = s3.list_objects_v2(Bucket=settings.minio_raw_bucket)
            objects = response.get("Contents", [])
            if objects:
                file_df = pd.DataFrame(objects)[["Key", "LastModified", "Size"]]
                st.dataframe(file_df, use_container_width=True)
            else:
                st.info("No files in MinIO raw bucket yet. Run the pipeline to generate raw landing files.")
        except Exception as e:
            st.error(f"MinIO connection error: {e}")

    with hop_tab2:
        st.subheader("Operational Staging Layer: PostgreSQL")
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
            st.error(f"PostgreSQL connection error: {e}")

    with hop_tab3:
        st.subheader("Curated Warehouse Layer: ClickHouse Star Schema")
        try:
            ch = get_clickhouse_client()
            fact_orders = ch.query_df("SELECT * FROM fact_delivery_sla FINAL ORDER BY created_at DESC LIMIT 50")
            fact_pings = ch.query_df("SELECT * FROM fact_telemetry_pings FINAL ORDER BY recorded_at DESC LIMIT 50")
            dim_couriers = ch.query_df("SELECT * FROM dim_couriers FINAL")

            st.markdown("#### `fact_delivery_sla` (Latest 50 Curated Orders)")
            st.dataframe(fact_orders, use_container_width=True)

            st.markdown("#### `fact_telemetry_pings` (Latest 50 Curated Telemetry Pings)")
            st.dataframe(fact_pings, use_container_width=True)

            st.markdown("#### `dim_couriers` (Dimension Table)")
            st.dataframe(dim_couriers, use_container_width=True)
        except Exception as e:
            st.error(f"ClickHouse connection error: {e}")

    with hop_tab4:
        st.subheader("Serving Layer: Consumer Analytical Views")
        try:
            ch = get_clickhouse_client()
            hub_view = ch.query_df("SELECT * FROM view_daily_hub_sla_summary ORDER BY total_orders DESC")
            courier_view = ch.query_df("SELECT * FROM view_courier_sla_leaderboard ORDER BY total_pings DESC")

            st.markdown("#### `view_daily_hub_sla_summary` (Hub Route SLA Performance)")
            st.dataframe(hub_view, use_container_width=True)

            st.markdown("#### `view_courier_sla_leaderboard` (Courier Performance Leaderboard)")
            st.dataframe(courier_view, use_container_width=True)
        except Exception as e:
            st.error(f"ClickHouse serving view error: {e}")

# --- Module 4: Serving Analytics ---
elif navigation == "Serving & SLA Analytics":
    st.header("📊 Delivery SLA & Courier Telemetry Analytics (Serving Layer)")

    try:
        ch = get_clickhouse_client()
        hub_df = ch.query_df("SELECT * FROM view_daily_hub_sla_summary")
        telemetry_df = ch.query_df("SELECT * FROM fact_telemetry_pings FINAL LIMIT 2000")

        if not hub_df.empty:
            total_orders = hub_df["total_orders"].sum()
            breached_orders = hub_df["breached_orders"].sum()
            compliance_pct = round((1.0 - (breached_orders / total_orders)) * 100, 2) if total_orders > 0 else 0

            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Total Curated Orders", total_orders)
            col_m2.metric("SLA Breached Orders", breached_orders)
            col_m3.metric("Overall SLA Compliance", f"{compliance_pct}%")

            st.subheader("Route SLA Compliance Rate (%)")
            hub_df["route"] = hub_df["origin_hub"] + " ➡️ " + hub_df["dest_hub"]
            fig_bar = px.bar(
                hub_df,
                x="route",
                y="sla_compliance_pct",
                color="sla_compliance_pct",
                color_continuous_scale="RdYlGn",
                title="SLA Compliance Rate by Fulfillment Route",
                labels={"sla_compliance_pct": "Compliance %"}
            )
            st.plotly_chart(fig_bar, use_container_width=True)

            if not telemetry_df.empty:
                st.subheader("Courier Telemetry Speed vs Battery Distribution")
                fig_scatter = px.scatter(
                    telemetry_df,
                    x="speed_kmh",
                    y="battery_pct",
                    color="courier_id",
                    title="Live Driver Fleet Telemetry",
                    labels={"speed_kmh": "Speed (km/h)", "battery_pct": "Battery (%)"}
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info("No curated analytical data found. Run the pipeline to populate ClickHouse tables!")
    except Exception as e:
        st.warning(f"Could not load analytics: {e}")

# --- Module 5: Documentation ---
elif navigation == "Documentation & Architecture":
    st.header("📄 Project Plan & Architecture Documentation")
    doc_choice = st.radio("Select Document", ["docs/PROJECT_PLAN.md", "README.md"])

    file_path = os.path.join(os.path.dirname(__file__), "../..", doc_choice)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f.read())
    else:
        st.error(f"Document file {doc_choice} not found.")
