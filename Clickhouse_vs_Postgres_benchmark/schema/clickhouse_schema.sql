-- ClickHouse Schema DDL for Analytical Benchmark

DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_store;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_customer (
    customer_id UInt32,
    first_name String,
    last_name String,
    email String,
    country String,
    segment String,
    signup_date Date
) ENGINE = MergeTree()
ORDER BY customer_id;

CREATE TABLE dim_product (
    product_id UInt32,
    product_name String,
    category String,
    sub_category String,
    brand String,
    unit_cost Float64
) ENGINE = MergeTree()
ORDER BY product_id;

CREATE TABLE dim_store (
    store_id UInt16,
    store_name String,
    city String,
    state String,
    region String,
    store_type String
) ENGINE = MergeTree()
ORDER BY store_id;

CREATE TABLE dim_date (
    date_id Date,
    year UInt16,
    quarter UInt8,
    month UInt8,
    day_of_week UInt8,
    is_weekend UInt8
) ENGINE = MergeTree()
ORDER BY date_id;

CREATE TABLE fact_sales (
    sale_id UInt64,
    customer_id UInt32,
    product_id UInt32,
    store_id UInt16,
    date_id Date,
    quantity UInt16,
    unit_price Float64,
    discount Float32,
    tax_amount Float64,
    total_amount Float64
) ENGINE = MergeTree()
PRIMARY KEY (store_id, date_id, product_id)
ORDER BY (store_id, date_id, product_id);
