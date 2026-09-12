-- Add on to Business Qn 5
-- Extension: Whether delays are affected by distance and product sizes?
-- Grain: 1 row per (distance_bucket, size_bucket) (linked by product_id, seller_id, order_id)

WITH joined_items AS (
    SELECT
        s.order_id,
        s.product_id,
        s.seller_id,
        d.product_weight_g,
        d.product_dimension,
        int_d.distance_meters,
        f.delivery_status
    FROM {{ ref('stg_order_items') }} AS s
    LEFT JOIN {{ ref('dim_products') }} AS d ON s.product_id = d.product_id
    LEFT JOIN {{ ref('int_sell_cust_distance') }} AS int_d ON s.order_id = int_d.order_id AND s.seller_id = int_d.seller_id
    LEFT JOIN {{ ref('fact_orders') }} AS f ON s.order_id = f.order_id
),

bucketed_items AS (
    SELECT
        *,
        CASE
            WHEN distance_meters / 1000 <= 100 THEN 'Zone 1'
            WHEN distance_meters / 1000 <= 500 THEN 'Zone 2'
            WHEN distance_meters / 1000 <= 1500 THEN 'Zone 3'
            ELSE 'Zone 4'
        END AS distance_bucket,

        CASE GREATEST(
            CASE
                WHEN product_dimension <= 80  THEN 1
                WHEN product_dimension <= 120 THEN 2
                WHEN product_dimension <= 200 THEN 3
                WHEN product_dimension <= 300 THEN 4
                ELSE 5
            END,
            CASE
                WHEN product_weight_g <= 5000  THEN 1
                WHEN product_weight_g <= 10000 THEN 2
                WHEN product_weight_g <= 20000 THEN 3
                WHEN product_weight_g <= 30000 THEN 4
                ELSE 1
            END
        )
            WHEN 1 THEN 'S'
            WHEN 2 THEN 'M'
            WHEN 3 THEN 'L'
            WHEN 4 THEN 'XL'
            ELSE 'Too Large or Too Heavy for Delivery'
        END AS size_bucket
    FROM joined_items
    WHERE product_weight_g IS NOT NULL
      AND product_dimension IS NOT NULL
      AND distance_meters IS NOT NULL
      AND delivery_status IS NOT NULL
)

SELECT
    distance_bucket,
    size_bucket,
    COUNT(*) AS order_item_count,
    SAFE_DIVIDE(
        COUNTIF(delivery_status LIKE 'late%'),
        COUNT(*)
    ) AS late_pct
FROM bucketed_items
GROUP BY distance_bucket, size_bucket
ORDER BY
    distance_bucket,
    CASE size_bucket
        WHEN 'S'  THEN 1
        WHEN 'M'  THEN 2
        WHEN 'L'  THEN 3
        WHEN 'XL' THEN 4
        ELSE 5
    END