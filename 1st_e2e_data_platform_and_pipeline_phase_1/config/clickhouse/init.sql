-- FastRoute Logistics ClickHouse OLAP Initialization DDL
-- Phase 1 Walking Skeleton

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

-- Dimension: Hubs
CREATE TABLE IF NOT EXISTS dim_hubs (
    hub_id String,
    hub_name String,
    city String,
    latitude Float64,
    longitude Float64,
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY hub_id;

-- Fact Table: Delivery SLA Performance
CREATE TABLE IF NOT EXISTS fact_delivery_sla (
    order_id String,
    tracking_number String,
    customer_id String,
    origin_hub String,
    dest_hub String,
    package_weight_kg Float32,
    promised_hours UInt16,
    actual_hours Float32,
    is_sla_breached UInt8,
    delivery_status String,
    created_date Date,
    created_at DateTime,
    delivered_at DateTime,
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
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
    recorded_at DateTime,
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(ping_date)
ORDER BY (ping_date, courier_id, recorded_at, ping_id);

-- Serving View: Daily Hub SLA Summary (Consumer Analytical View)
CREATE OR REPLACE VIEW view_daily_hub_sla_summary AS
SELECT
    created_date,
    origin_hub,
    dest_hub,
    count() AS total_orders,
    sum(is_sla_breached) AS breached_orders,
    count() - sum(is_sla_breached) AS on_time_orders,
    round((1.0 - (sum(is_sla_breached) / count())) * 100, 2) AS sla_compliance_pct,
    round(avg(actual_hours), 2) AS avg_delivery_hours
FROM fact_delivery_sla FINAL
GROUP BY created_date, origin_hub, dest_hub;

-- Serving View: Courier Performance Leaderboard
CREATE OR REPLACE VIEW view_courier_sla_leaderboard AS
SELECT
    p.ping_date,
    p.courier_id,
    c.full_name,
    c.vehicle_type,
    c.home_hub,
    count() AS total_pings,
    round(avg(p.speed_kmh), 1) AS avg_speed_kmh,
    round(avg(p.battery_pct), 1) AS avg_battery_pct
FROM fact_telemetry_pings AS p FINAL
LEFT JOIN dim_couriers AS c FINAL ON p.courier_id = c.courier_id
GROUP BY p.ping_date, p.courier_id, c.full_name, c.vehicle_type, c.home_hub;
