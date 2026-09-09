-- Business Question 8+9: Which products experience more delivery problems, by product categories and weight or size?

WITH product_items AS ( 
  -- Step 1: Count items and find distinct order-product combinations 
  SELECT 
    order_id, 
    product_id, 
    COUNT(*) AS items_in_order 
  FROM {{ ref('stg_order_items') }} 
  GROUP BY order_id, product_id 
),

-- Step 2: Join fact_orders and stg_products. Also, evaluate size/dimension buckets and weight buckets, 
-- take the larger of the two and establish size buckets using Shopee Ninjavan parcel size buckets 
-- https://seller.shopee.sg/edu/article/7039, seems to match international standards and the Olist raw data, 
-- where weight>30kg or product dimension<300cm is too large for delivery

product_size_bucket_table AS (
  -- Step 2: Join fact_orders and stg_products and calculate row-level attributes
  SELECT 
    p.product_category_name_english, 
    p.product_category_buckets,
    
     -- Evaluate size bucket using product dimensions
    CASE 
      WHEN product_dimension <= 80  THEN 1 -- 'S'
      WHEN product_dimension <= 120 THEN 2 -- 'M'
      WHEN product_dimension <= 200 THEN 3 -- 'L'
      WHEN product_dimension <= 300 THEN 4 -- 'XL'
      ELSE 5 -- Outlier, will not be accepted for delivery
    END AS dim_score,

    -- Evaluate size bucket using weight boundaries
    CASE 
      WHEN product_weight_g <= 5000  THEN 1 -- 'S'
      WHEN product_weight_g <= 10000 THEN 2 -- 'M'
      WHEN product_weight_g <= 20000 THEN 3 -- 'L'
      WHEN product_weight_g <= 30000 THEN 4 -- 'XL'
      ELSE 1 -- >30 kg weight is treated as outliers, assume errors in data, defaults back to product_dimension
    END AS weight_score,

    pi.items_in_order,
    f.total_delivery_days,
    f.delivery_status,
    f.order_revenue,
    f.order_freight
  FROM product_items AS pi 
  JOIN {{ ref('fact_orders') }} AS f ON pi.order_id = f.order_id 
  JOIN {{ ref('dim_products') }} AS p ON pi.product_id = p.product_id 
  WHERE p.product_weight_g IS NOT NULL 
    AND p.product_length_cm IS NOT NULL 
    AND p.product_height_cm IS NOT NULL 
    AND p.product_width_cm IS NOT NULL
),

-- Step 3: Determine the final product size bucket using the maximum of the dimension and weight scores, then map to the corresponding size label
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

-- Step 4: Aggregate final metrics for analysis by product category and size/weight buckets, including counts of items, delivery performance, and revenue/freight metrics
SELECT
  product_category_buckets,
  product_size_buckets, 
  SUM(items_in_order) AS product_item_count, 
  AVG(total_delivery_days) AS avg_delivery_days, 
  SUM(CASE WHEN delivery_status = 'not_delivered' THEN items_in_order ELSE 0 END) AS not_delivered_item_count, 
  SUM(CASE WHEN delivery_status IN ('early', 'on_time') THEN items_in_order ELSE 0 END) AS on_time_item_count, 
  SUM(CASE WHEN delivery_status LIKE 'late%' THEN items_in_order ELSE 0 END) AS late_item_count, 
  SAFE_DIVIDE( 
    SUM(CASE WHEN delivery_status LIKE 'late%' THEN items_in_order ELSE 0 END), 
    SUM(items_in_order) 
  ) AS late_item_pct,
  SUM(order_revenue) AS total_revenue, 
  SUM(order_freight) AS total_freight,
  SUM(order_revenue) / SUM(items_in_order) AS avg_revenue_per_item,
  SUM(order_freight) / SUM(items_in_order) AS avg_freight_per_item
FROM product_final_size_bucket
GROUP BY 
  product_category_buckets, 
  product_size_buckets
ORDER BY 
  product_category_buckets, 
    CASE product_size_buckets
    WHEN 'S'  THEN 1
    WHEN 'M' THEN 2
    WHEN 'L'  THEN 3
    WHEN 'XL' THEN 4
    ELSE 5 -- Outlier, will not be accepted for delivery
    END
  