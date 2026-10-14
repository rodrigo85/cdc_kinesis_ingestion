-- =============================================================================
-- PostgreSQL CDC Initialization Script for AWS DMS / Kinesis Streaming
-- =============================================================================

-- 1. Ensure Logical Replication is verified
DO $$
BEGIN
    IF current_setting('wal_level') != 'logical' THEN
        RAISE EXCEPTION 'wal_level must be set to "logical" for CDC. Please check PostgreSQL startup parameters.';
    END IF;
END $$;

-- 2. Create Schema
CREATE SCHEMA IF NOT EXISTS delivery;

-- 3. Create Target Table
CREATE TABLE IF NOT EXISTS delivery.orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) NOT NULL UNIQUE,
    customer_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'Pending',
    total_amount NUMERIC(10, 2) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'Pending',
    delivery_address TEXT,
    delivery_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    estimated_delivery_time TIMESTAMP WITH TIME ZONE,
    driver_id INT,
    restaurant_id INT
);

-- 4. Create Indexes for Query & Streaming Performance
CREATE INDEX IF NOT EXISTS idx_orders_status ON delivery.orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON delivery.orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_restaurant_id ON delivery.orders(restaurant_id);

-- 5. Trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION delivery.update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_orders_updated_at ON delivery.orders;
CREATE TRIGGER trg_orders_updated_at
BEFORE UPDATE ON delivery.orders
FOR EACH ROW
EXECUTE FUNCTION delivery.update_timestamp();

-- 6. Configure Table REPLICA IDENTITY
-- REPLICA IDENTITY FULL ensures UPDATE and DELETE records include old column values for CDC
ALTER TABLE delivery.orders REPLICA IDENTITY FULL;

-- 7. Create Dedicated Replication User & Roles (Big Tech Security Best Practice)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dms_user') THEN
        CREATE USER dms_user WITH REPLICATION PASSWORD 'DmsSecurePassword2026!';
    END IF;
END $$;

GRANT USAGE ON SCHEMA delivery TO dms_user;
GRANT SELECT ON ALL TABLES IN SCHEMA delivery TO dms_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA delivery GRANT SELECT ON TABLES TO dms_user;

-- 8. Create Publication for AWS DMS / pglogical CDC
CREATE PUBLICATION delivery_publication FOR TABLE delivery.orders;

-- 9. Verification Message
DO $$
BEGIN
    RAISE NOTICE 'Delivery CDC schema and publication initialized successfully.';
END $$;
