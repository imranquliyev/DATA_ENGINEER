-- FastRoute Logistics Staging & Metadata Initialization Schema
-- Phase 1 Walking Skeleton

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS audit;

-- Operational Staging Orders
CREATE TABLE IF NOT EXISTS staging.staging_orders (
    order_id VARCHAR(64) PRIMARY KEY,
    tracking_number VARCHAR(64) NOT NULL,
    customer_id VARCHAR(64),
    origin_hub VARCHAR(32) NOT NULL,
    dest_hub VARCHAR(32) NOT NULL,
    package_weight_kg NUMERIC(6, 2),
    promised_hours INTEGER,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    batch_date DATE NOT NULL,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_staging_orders_batch_date ON staging.staging_orders (batch_date);

-- Operational Staging Driver Telemetry Pings
CREATE TABLE IF NOT EXISTS staging.staging_telemetry (
    ping_id VARCHAR(64) PRIMARY KEY,
    courier_id VARCHAR(32) NOT NULL,
    latitude NUMERIC(9, 6),
    longitude NUMERIC(9, 6),
    speed_kmh NUMERIC(5, 2),
    battery_pct INTEGER,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    batch_date DATE NOT NULL,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_staging_telemetry_batch_date ON staging.staging_telemetry (batch_date);

-- Quality Audit Quarantine Log
CREATE TABLE IF NOT EXISTS audit.quality_audit_logs (
    audit_id SERIAL PRIMARY KEY,
    batch_id VARCHAR(64) NOT NULL,
    logical_date DATE NOT NULL,
    dataset_name VARCHAR(64) NOT NULL,
    total_records INTEGER NOT NULL,
    passed_records INTEGER NOT NULL,
    failed_records INTEGER NOT NULL,
    failure_reasons JSONB,
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Dimension couriers source table in PostgreSQL
CREATE TABLE IF NOT EXISTS staging.couriers (
    courier_id VARCHAR(32) PRIMARY KEY,
    full_name VARCHAR(128) NOT NULL,
    vehicle_type VARCHAR(32) NOT NULL,
    home_hub VARCHAR(32) NOT NULL,
    active_status BOOLEAN DEFAULT TRUE
);

INSERT INTO staging.couriers (courier_id, full_name, vehicle_type, home_hub, active_status)
VALUES 
    ('C-101', 'Elvin Hasanov', 'Van', 'HUB-BAKU-NORTH', TRUE),
    ('C-102', 'Aysel Mammadova', 'Scooter', 'HUB-BAKU-CENTER', TRUE),
    ('C-103', 'Rashad Aliyev', 'Truck', 'HUB-SUMGAYIT', TRUE),
    ('C-104', 'Nigar Huseynova', 'Van', 'HUB-GANJA', TRUE)
ON CONFLICT (courier_id) DO NOTHING;

-- Dimension hubs source table in PostgreSQL
CREATE TABLE IF NOT EXISTS staging.hubs (
    hub_id VARCHAR(32) PRIMARY KEY,
    hub_name VARCHAR(128) NOT NULL,
    city VARCHAR(64) NOT NULL,
    latitude NUMERIC(9, 6) NOT NULL,
    longitude NUMERIC(9, 6) NOT NULL
);

INSERT INTO staging.hubs (hub_id, hub_name, city, latitude, longitude)
VALUES
    ('HUB-BAKU-NORTH', 'Baku North Logistics Center', 'Baku', 40.420000, 49.880000),
    ('HUB-BAKU-CENTER', 'Baku Central Dispatch Terminal', 'Baku', 40.380000, 49.850000),
    ('HUB-BAKU-SOUTH', 'Baku South Transit Station', 'Baku', 40.340000, 49.820000),
    ('HUB-SUMGAYIT', 'Sumgayit Regional Hub', 'Sumgayit', 40.590000, 49.630000),
    ('HUB-GANJA', 'Ganja Fulfillment Hub', 'Ganja', 40.680000, 46.360000)
ON CONFLICT (hub_id) DO NOTHING;
