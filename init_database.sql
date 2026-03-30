-- Create database and user (run as postgres superuser)
CREATE DATABASE analytics;
CREATE USER pipeline_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE analytics TO pipeline_user;

-- Connect to analytics database and create tables
\c analytics;

-- Customers source table
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    registration_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Customer dimension table (for SCD2)
CREATE TABLE dim_customers (
    dim_customer_key SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    effective_start_date DATE NOT NULL,
    effective_end_date DATE NOT NULL,
    is_current BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily order facts table
CREATE TABLE fact_daily_orders (
    order_date DATE,
    customer_id INTEGER,
    total_sales DECIMAL(10,2),
    order_count INTEGER,
    avg_order_value DECIMAL(10,2),
    unique_orders INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_date, customer_id)
);

-- Insert sample customer data
INSERT INTO customers VALUES
(1001, 'Alice Johnson', 'alice.johnson@email.com', '2023-01-15', 'active', '2024-02-01 10:00:00'),
(1002, 'Bob Smith', 'bob.smith@email.com', '2023-02-20', 'active', '2024-02-01 10:00:00'),
(1003, 'Carol Davis', 'carol.davis@email.com', '2023-03-10', 'inactive', '2024-01-28 15:30:00'),
(1004, 'David Wilson', 'david.wilson@email.com', '2023-04-05', 'active', '2024-02-01 10:00:00'),
(1005, 'Eve Brown', 'eve.brown@email.com', '2023-05-12', 'active', '2024-01-30 09:15:00');

-- Grant permissions to pipeline user
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO pipeline_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO pipeline_user;