-- FastRoute Logistics ClickHouse OLAP Initialization DDL

CREATE DATABASE IF NOT EXISTS fastroute_analytics;

USE fastroute_analytics;

-- Dimension: Couriers
CREATE TABLE IF NOT EXISTS dim_couriers (
    courier_id String,
    full_name String,
    vehicle_type String,
    home_hub String,
    active_status UInt8,
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY courier_id;

-- Fact Table: Delivery SLA Performance
CREATE TABLE IF NOT EXISTS fact_delivery_sla (
    order_id String,
    tracking_number String,
    origin_hub String,
    dest_hub String,
    package_weight_kg Float32,
    promised_hours UInt16,
    actual_hours Float32,
    is_sla_breached UInt8,
    delivery_status String,
    created_date Date,
    created_at DateTime,
    delivered_at DateTime
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(created_date)
ORDER BY (created_date, origin_hub, dest_hub, order_id);

-- Fact Table: High-Frequency Telemetry Pings
CREATE TABLE IF NOT EXISTS fact_telemetry_pings (
    ping_id String,
    courier_id String,
    latitude Float64,
    longitude Float64,
    speed_kmh Float32,
    battery_pct UInt8,
    is_anomalous UInt8,
    ping_date Date,
    recorded_at DateTime
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(ping_date)
ORDER BY (ping_date, courier_id, recorded_at);
