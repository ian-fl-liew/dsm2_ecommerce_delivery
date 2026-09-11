-- Business Question 8+9: Which products experience more delivery problems, by product categories and weight or size?
--
-- Reads fact_orders directly now that it is item grain -- one row per line item already,
-- so the old product_items CTE is gone along with its join on order_id alone, which would
-- fan out ((order,product) rows x every item row of the order).
--
-- Money metrics use item_price/item_freight, not order_revenue/order_freight: an order's
-- revenue cannot be attributed to one product bucket when the order spans buckets.

-- Step 1: Join fact_orders and dim_products. Evaluate size/dimension buckets and weight
-- buckets, take the larger of the two and establish size buckets using Shopee Ninjavan
-- parcel size buckets https://seller.shopee.sg/edu/article/7039, seems to match
-- international standards and the Olist raw data, where weight>30kg or product
-- dimension<300cm is too large for delivery

WITH product_size_bucket_table AS (
  SELECT
    p.product_category_name_english,
    p.product_category_buckets,

    -- Evaluate size bucket using product dimensions
    CASE
      WHEN p.product_dimension <= 80  THEN 1 -- 'S'
      WHEN p.product_dimension <= 120 THEN 2 -- 'M'
      WHEN p.product_dimension <= 200 THEN 3 -- 'L'
      WHEN p.product_dimension <= 300 THEN 4 -- 'XL'
      ELSE 5 -- Outlier, will not be accepted for delivery
    END AS dim_score,

    -- Evaluate size bucket using weight boundaries
    CASE
      WHEN p.product_weight_g <= 5000  THEN 1 -- 'S'
      WHEN p.product_weight_g <= 10000 THEN 2 -- 'M'
      WHEN p.product_weight_g <= 20000 THEN 3 -- 'L'
      WHEN p.product_weight_g <= 30000 THEN 4 -- 'XL'
      ELSE 1 -- >30 kg weight is treated as outliers, assume errors in data, defaults back to product_dimension
    END AS weight_score,

    f.total_delivery_days,
    f.delivery_status,
    f.item_price,
    f.item_freight
  FROM {{ ref('fact_orders') }} AS f
  JOIN {{ ref('dim_products') }} AS p ON f.product_id = p.product_id
  WHERE p.product_weight_g IS NOT NULL
    AND p.product_length_cm IS NOT NULL
    AND p.product_height_cm IS NOT NULL
    AND p.product_width_cm IS NOT NULL
),

-- Step 2: Determine the final product size bucket using the maximum of the dimension and weight scores, then map to the corresponding size label
product_final_size_bucket AS (
  SELECT
    *,
    -- Use GREATEST to pick the larger size tier between pdt dimension and weight, then map the numeric score back to its text label
    CASE GREATEST(dim_score, weight_score)
      WHEN 1 THEN 'S'
      WHEN 2 THEN 'M'
      WHEN 3 THEN 'L'
      WHEN 4 THEN 'XL'
      ELSE 'Too Large or Too Heavy for Delivery' -- Outlier, will not be accepted for delivery
    END AS product_size_buckets
  FROM product_size_bucket_table
)

-- Step 3: Aggregate final metrics by product category and size/weight buckets.
-- One row per item now, so COUNT replaces the old SUM(items_in_order).
SELECT
  product_category_buckets,
  product_size_buckets,
  COUNT(*) AS product_item_count,
  AVG(total_delivery_days) AS avg_delivery_days,
  COUNTIF(delivery_status = 'not_delivered') AS not_delivered_item_count,
  COUNTIF(delivery_status IN ('early', 'on_time')) AS on_time_item_count,
  COUNTIF(delivery_status LIKE 'late%') AS late_item_count,
  SAFE_DIVIDE(COUNTIF(delivery_status LIKE 'late%'), COUNT(*)) AS late_item_pct,
  SUM(item_price) AS total_revenue,
  SUM(item_freight) AS total_freight,
  SAFE_DIVIDE(SUM(item_price), COUNT(*)) AS avg_revenue_per_item,
  SAFE_DIVIDE(SUM(item_freight), COUNT(*)) AS avg_freight_per_item
FROM product_final_size_bucket
GROUP BY
  product_category_buckets,
  product_size_buckets
ORDER BY
  product_category_buckets,
  CASE product_size_buckets
    WHEN 'S'  THEN 1
    WHEN 'M'  THEN 2
    WHEN 'L'  THEN 3
    WHEN 'XL' THEN 4
    ELSE 5 -- Outlier, will not be accepted for delivery
  END
