-- Generated Code for MAP_ERP_ORDERS_TO_FACT_SALES (Version v1.00.00)
-- Generation Timestamp: 2025-10-18T00:30:00

BEGIN TRANSACTION;

-- --------------------------------------------------------------------
-- 1. Create or replace the target fact table
-- --------------------------------------------------------------------
CREATE OR REPLACE TABLE Fact_Sales (
    Target_Order_ID          STRING      NOT NULL,
    Target_Amount_Local      DECIMAL(20,4) DEFAULT 0,
    Target_Amount_USD        DECIMAL(20,4) DEFAULT 0,
    Target_Customer_Name     STRING,
    Target_Distinct_Items    INTEGER     DEFAULT 0,
    Target_Status_Category   VARCHAR(20) DEFAULT 'Unknown',
    ETL_Load_Timestamp       TIMESTAMP_NTZ,
    PRIMARY KEY (Target_Order_ID)
);

COMMENT ON TABLE Fact_Sales IS 'Fact table for sales derived from ERP orders';

-- --------------------------------------------------------------------
-- 2. Build the source dataset using CTEs
-- --------------------------------------------------------------------
WITH
    -- Deduplicate orders: keep the most recent record per order_id
    o AS (
        SELECT
            order_id,
            last_modified_date,
            customer_id,
            order_date,
            currency_code,
            status,
            ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY last_modified_date DESC) AS rn
        FROM orders
        WHERE is_active = TRUE
    ),
    -- Aggregate order items to calculate total amount and distinct item count
    oi_agg AS (
        SELECT
            order_id,
            SUM(quantity * unit_price) AS total_amount,
            COUNT(DISTINCT item_id) AS distinct_items
        FROM order_items
        GROUP BY order_id
    ),
    -- Final source table ready for merge
    src AS (
        SELECT
            o.order_id                                          AS Target_Order_ID,
            COALESCE(oi_agg.total_amount, 0)                    AS Target_Amount_Local,
            COALESCE(oi_agg.total_amount, 0) *
            COALESCE(ex.ExchangeRate, 1.0)                      AS Target_Amount_USD,
            COALESCE(c.customer_name, 'Unknown')                AS Target_Customer_Name,
            COALESCE(oi_agg.distinct_items, 0)                  AS Target_Distinct_Items,
            CASE
                WHEN o.status = 'Completed' THEN 'Fulfilled'
                WHEN o.status = 'Shipped'   THEN 'Fulfilled'
                WHEN o.status = 'Cancelled' THEN 'Cancelled'
                ELSE 'Open'
            END                                                AS Target_Status_Category,
            CURRENT_TIMESTAMP()                                 AS ETL_Load_Timestamp
        FROM o
        INNER JOIN customers c
            ON o.customer_id = c.customer_id
        INNER JOIN oi_agg
            ON o.order_id = oi_agg.order_id
        LEFT JOIN Dim_Exchange_Rates