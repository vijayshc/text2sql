-- Generated Code for MAP_ERP_ORDERS_TO_FACT_SALES
-- Generation Timestamp: 2025-10-21T12:00:00

CREATE OR REPLACE PROCEDURE run_map_erp_orders_to_fact_sales()
RETURNS STRING
LANGUAGE SQL
AS
$$
DECLARE
    v_msg STRING;
    v_src_cnt NUMBER;
BEGIN
    /* --------------------------------------------------------------------
       1. Ensure the target fact table exists with the correct schema
       -------------------------------------------------------------------- */
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
    COMMENT ON COLUMN Fact_Sales.Target_Order_ID          IS 'Unique identifier for the order';
    COMMENT ON COLUMN Fact_Sales.Target_Amount_Local      IS 'Total order amount in original currency';
    COMMENT ON COLUMN Fact_Sales.Target_Amount_USD        IS 'Total order amount converted to USD';
    COMMENT ON COLUMN Fact_Sales.Target_Customer_Name     IS 'Name of the customer';
    COMMENT ON COLUMN Fact_Sales.Target_Distinct_Items    IS 'Number of unique items in the order';
    COMMENT ON COLUMN Fact_Sales.Target_Status_Category   IS 'Categorized status based on source status value';
    COMMENT ON COLUMN Fact_Sales.ETL_Load_Timestamp       IS 'Timestamp when the record was loaded';

    /* --------------------------------------------------------------------
       2. Build source dataset and count rows
       -------------------------------------------------------------------- */
    WITH
        /* Deduplicate orders: keep the most recent record per order_id */
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
        /* Aggregate order items to calculate total amount and distinct item count */
        oi_agg AS (
            SELECT
                order_id,
                SUM(quantity * unit_price) AS total_amount,
                COUNT(DISTINCT item_id) AS distinct_items
            FROM order_items
            GROUP BY order_id
        ),
        /* Final source projection */
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
                END                                                  AS Target_Status_Category,
                CURRENT_TIMESTAMP()                                 AS ETL_Load_Timestamp
            FROM o
            INNER JOIN customers c
                ON o.customer_id = c.customer_id
            INNER JOIN oi_agg
                ON o.order_id = oi_agg.order_id
            LEFT JOIN Dim_Exchange_Rates ex
                ON o.order_date = ex.RateDate
               AND o.currency_code = ex.CurrencyCode
            WHERE o.rn = 1
        )
    SELECT COUNT(*) INTO v_src_cnt FROM src;

    /* If no source data, exit early */
    IF v_src_cnt = 0 THEN
        v_msg := 'No source data to merge.';
        RETURN v_msg;
    END IF;

    /* --------------------------------------------------------------------
       3. Merge source data into the fact table
       -------------------------------------------------------------------- */
    MERGE INTO Fact_Sales tgt
    USING src
    ON tgt.Target_Order_ID = src.Target_Order_ID
    WHEN MATCHED THEN
        UPDATE SET
            tgt.Target_Amount_Local   = src.Target_Amount_Local,
            tgt.Target_Amount_USD     = src.Target_Amount_USD,
            tgt.Target_Customer_Name  = src.Target_Customer_Name,
            tgt.Target_Distinct_Items = src.Target_Distinct_Items,
            tgt.Target_Status_Category = src.Target_Status_Category,
            tgt.ETL_Load_Timestamp   = src.ETL_Load_Timestamp
    WHEN NOT MATCHED THEN
        INSERT (
            Target_Order_ID,
            Target_Amount_Local,
            Target_Amount_USD,
            Target_Customer_Name,
            Target_Distinct_Items,
            Target_Status_Category,
            ETL_Load_Timestamp
        )
        VALUES (
            src.Target_Order_ID,
            src.Target_Amount_Local,
            src.Target_Amount_USD,
            src.Target_Customer_Name,
            src.Target_Distinct_Items,
            src.Target_Status_Category,
            src.ETL_Load_Timestamp
        );

    v_msg := 'Merge completed successfully. Rows processed: ' || v_src_cnt;
    RETURN v_msg;
EXCEPTION
    WHEN OTHERS THEN
        v_msg := 'Error during merge: ' || SQLERRM;
        RETURN v_msg;
END;
$$;
--- End of procedure definition ---