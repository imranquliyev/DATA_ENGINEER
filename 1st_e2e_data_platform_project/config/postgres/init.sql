-- FastRoute Logistics Staging & Metadata Initialization Schema

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
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Operational Staging Driver Telemetry Pings
CREATE TABLE IF NOT EXISTS staging.staging_telemetry (
    ping_id VARCHAR(64) PRIMARY KEY,
    courier_id VARCHAR(32) NOT NULL,
    latitude NUMERIC(9, 6),
    longitude NUMERIC(9, 6),
    speed_kmh NUMERIC(5, 2),
    battery_pct INTEGER,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Quality Audit Quarantine Log
CREATE TABLE IF NOT EXISTS audit.quality_audit_logs (
    audit_id SERIAL PRIMARY KEY,
    batch_id VARCHAR(64) NOT NULL,
    dataset_name VARCHAR(64) NOT NULL,
    total_records INTEGER NOT NULL,
    passed_records INTEGER NOT NULL,
    failed_records INTEGER NOT NULL,
    failure_reasons JSONB,
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Pre-populate sample couriers & hubs metadata table
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
