-- Business Question 8+9: Which products experience more delivery problems, by product categories and weight or size?


WITH base_metrics AS (
  -- Step 1: Join fact_orders and dim_products and calculate row-level attributes
  SELECT
    p.product_category_name_english,

    -- Evaluate the max between physical weight and volumetric weight. Volumetric weight is calculated as (length * height * width) / 5, which is a common formula used in logistics (eg. DHL) to account for the space a package occupies.
    CASE
      WHEN GREATEST(
        p.product_weight_g,
        (p.product_length_cm * p.product_height_cm * p.product_width_cm / 5)
      ) <= 250 THEN '1. Ultra-Light (<=250g)'

      WHEN GREATEST(
        p.product_weight_g,
        (p.product_length_cm * p.product_height_cm * p.product_width_cm / 5)
      ) <= 1000 THEN '2. Light (251g-1kg)'

      WHEN GREATEST(
        p.product_weight_g,
        (p.product_length_cm * p.product_height_cm * p.product_width_cm / 5)
      ) <= 5000 THEN '3. Medium (1.01kg-5kg)'

      WHEN GREATEST(
        p.product_weight_g,
        (p.product_length_cm * p.product_height_cm * p.product_width_cm / 5)
      ) <= 15000 THEN '4. Heavy (5.01kg-15kg)'

      ELSE '5. Ultra-Heavy (>15kg)'
    END AS billable_weight_band,

    f.total_delivery_days,
    f.delivery_status
  FROM {{ ref('fact_orders') }} AS f
  JOIN {{ ref('dim_products') }} AS p ON f.product_id = p.product_id
)

-- Step 2: Aggregate final metrics safely -- one row per item, so COUNT replaces the
-- old SUM(items_in_order)
SELECT
  product_category_name_english,
  billable_weight_band,
  COUNT(*) AS product_item_count,
  AVG(total_delivery_days) AS avg_delivery_days,
  COUNTIF(delivery_status = 'not_delivered') AS not_delivered_item_count,
  COUNTIF(delivery_status IN ('early', 'on_time')) AS on_time_item_count,
  COUNTIF(delivery_status LIKE 'late%') AS late_item_count,
  SAFE_DIVIDE(
    COUNTIF(delivery_status LIKE 'late%'),
    COUNT(*)
  ) AS late_item_pct
FROM base_metrics
GROUP BY
  product_category_name_english,
  billable_weight_band
ORDER BY
  product_category_name_english,
  billable_weight_band
