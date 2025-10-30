-- Generated Code for MAP_ERP_ORDERS_TO_FACT_SALES
-- Generated at: 2025-10-31T00:00:35.156673

/*  
  MERGE statement to upsert sales fact data.
  Uses deduplicated orders, aggregated order items, and exchange rates.
  All transformations and calculations are applied as per mapping specification.
*/
MERGE INTO Fact_Sales tgt
USING (
  SELECT
    /* Unique identifier for the order */
    o.order_id                                 AS Target_Order_ID,

    /* Total order amount in original currency */
    oi_agg.total_amount                        AS Target_Amount_Local,

    /* Total order amount converted to USD */
    oi_agg.total_amount * COALESCE(ex.ExchangeRate, 1.0) AS Target_Amount_USD,

    /* Customer name */
    c.customer_name                            AS Target_Customer_Name,

    /* Number of distinct items in the order */
    oi_agg.distinct_items                      AS Target_Distinct_Items,

    /* Categorized status */
    CASE
      WHEN o.status = 'Completed' THEN 'Fulfilled'
      WHEN o.status = 'Shipped'   THEN 'Fulfilled'
      WHEN o.status = 'Cancelled' THEN 'Cancelled'
      ELSE 'Open'
    END                                         AS Target_Status_Category,

    /* ETL load timestamp */
    CURRENT_TIMESTAMP()                        AS ETL_Load_Timestamp

  FROM (
        /* Deduplicate orders by order_id using the latest last_modified_date */
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
      ) o

  INNER JOIN customers c
    ON o.customer_id = c.customer_id

  INNER JOIN (
        /* Aggregate order items per order */
        SELECT
          order_id,
          SUM(quantity * unit_price) AS total_amount,
          COUNT(DISTINCT item_id)    AS distinct_items
        FROM order_items
        GROUP BY order_id
      ) oi_agg
    ON o.order_id = oi_agg.order_id

  LEFT JOIN Dim_Exchange_Rates ex
    ON o.order_date = ex.RateDate
   AND o.currency_code = ex.CurrencyCode

  WHERE o.rn = 1  /* Keep only the latest record per order */
) src
ON tgt.Target_Order_ID = src.Target_Order_ID

/* Update existing records */
WHEN MATCHED THEN
  UPDATE SET
    tgt.Target_Amount_Local    = src.Target_Amount_Local,
    tgt.Target_Amount_USD      = src.Target_Amount_USD,
    tgt.Target_Customer_Name   = src.Target_Customer_Name,
    tgt.Target_Distinct_Items  = src.Target_Distinct_Items,
    tgt.Target_Status_Category = src.Target_Status_Category,
    tgt.ETL_Load_Timestamp     = src.ETL_Load_Timestamp

/* Insert new records */
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