-- SQL for MAP_ERP_ORDERS_TO_FACT_SALES
-- Assuming source tables: orders, customers, order_items, Dim_Exchange_Rates
-- Target table: Fact_Sales

-- 1. Create target table if it does not exist
CREATE TABLE IF NOT EXISTS Fact_Sales (
  Target_Order_ID STRING PRIMARY KEY,
  Target_Amount_Local DECIMAL(20,4) NOT NULL,
  Target_Amount_USD DECIMAL(20,4) NOT NULL,
  Target_Customer_Name STRING,
  Target_Distinct_Items INTEGER,
  Target_Status_Category STRING,
  ETL_Load_Timestamp TIMESTAMP_NTZ
);

-- 2. Merge data into Fact_Sales
MERGE INTO Fact_Sales AS tgt
USING (
  SELECT
    o.order_id AS Target_Order_ID,
    oi_agg.total_amount AS Target_Amount_Local,
    oi_agg.total_amount * COALESCE(ex.ExchangeRate, 1.0) AS Target_Amount_USD,
    c.customer_name AS Target_Customer_Name,
    oi_agg.distinct_items AS Target_Distinct_Items,
    CASE
      WHEN o.status = 'Completed' THEN 'Fulfilled'
      WHEN o.status = 'Shipped' THEN 'Fulfilled'
      WHEN o.status = 'Cancelled' THEN 'Cancelled'
      ELSE 'Open'
    END AS Target_Status_Category,
    CURRENT_TIMESTAMP() AS ETL_Load_Timestamp
  FROM (
    SELECT
      order_id,
      last_modified_date,
      customer_id,
      order_date,
      currency_code,
      status,
      ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY last_modified_date DESC) AS rn
    FROM orders
    WHERE is_active = true
  ) o
  INNER JOIN customers c ON o.customer_id = c.customer_id
  INNER JOIN (
    SELECT
      order_id,
      SUM(quantity * unit_price) AS total_amount,
      COUNT(DISTINCT item_id) AS distinct_items
    FROM order_items
    GROUP BY order_id
  ) oi_agg ON o.order_id = oi_agg.order_id
  LEFT JOIN Dim_Exchange_Rates ex ON o.order_date = ex.RateDate AND o.currency_code = ex.CurrencyCode
  WHERE o.rn = 1
) src
ON tgt.Target_Order_ID = src.Target_Order_ID
WHEN MATCHED THEN UPDATE SET
  tgt.Target_Amount_Local = src.Target_Amount_Local,
  tgt.Target_Amount_USD = src.Target_Amount_USD,
  tgt.Target_Customer_Name = src.Target_Customer_Name,
  tgt.Target_Distinct_Items = src.Target_Distinct_Items,
  tgt.Target_Status_Category = src.Target_Status_Category,
  tgt.ETL_Load_Timestamp = src.ETL_Load_Timestamp
WHEN NOT MATCHED THEN INSERT (
  Target_Order_ID,
  Target_Amount_Local,
  Target_Amount_USD,
  Target_Customer_Name,
  Target_Distinct_Items,
  Target_Status_Category,
  ETL_Load_Timestamp
) VALUES (
  src.Target_Order_ID,
  src.Target_Amount_Local,
  src.Target_Amount_USD,
  src.Target_Customer_Name,
  src.Target_Distinct_Items,
  src.Target_Status_Category,
  src.ETL_Load_Timestamp
);

-- End of MAP_ERP_ORDERS_TO_FACT_SALES
