DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_store;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_customer (
    customer_id Int32,
    first_name String,
    last_name String,
    email String,
    segment String,
    country String
) ENGINE = MergeTree()
ORDER BY customer_id;

CREATE TABLE dim_product (
    product_id Int32,
    product_name String,
    category String,
    brand String,
    unit_cost Float64
) ENGINE = MergeTree()
ORDER BY product_id;

CREATE TABLE dim_store (
    store_id Int32,
    store_name String,
    city String,
    state String,
    region String
) ENGINE = MergeTree()
ORDER BY store_id;

CREATE TABLE dim_date (
    date_key Int32,
    full_date Date,
    year Int32,
    quarter Int32,
    month Int32,
    day_of_week Int32
) ENGINE = MergeTree()
ORDER BY date_key;

CREATE TABLE fact_sales (
    order_id Int64,
    customer_id Int32,
    product_id Int32,
    store_id Int32,
    date_key Int32,
    order_timestamp DateTime,
    quantity Int32,
    unit_price Float64,
    discount_amount Float64
) ENGINE = MergeTree()
PRIMARY KEY (date_key, store_id)
ORDER BY (date_key, store_id, product_id, order_id);