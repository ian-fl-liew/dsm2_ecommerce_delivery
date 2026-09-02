-- Business Question 7: Which sellers are both high-volume AND poor performers?

WITH seller_items AS (
    -- Step 1: Count items and find distinct order-seller combinations
    SELECT 
        order_id,
        seller_id,
        COUNT(*) AS items_in_order
    FROM {{ ref('stg_order_items') }}
    GROUP BY order_id, seller_id
)

-- Step 2: Join back to orders and calculate final metrics
SELECT 
    si.seller_id,
    SUM(si.items_in_order) AS seller_item_count,
    SUM(CASE WHEN f.delivery_status = 'not_delivered' THEN si.items_in_order ELSE 0 END) AS not_delivered_item_count,
    SUM(CASE WHEN f.delivery_status IN ('early', 'on_time') THEN si.items_in_order ELSE 0 END) AS on_time_item_count,
    SUM(CASE WHEN f.delivery_status LIKE 'late%' THEN si.items_in_order ELSE 0 END) AS late_item_count,
    SAFE_DIVIDE(
        SUM(CASE WHEN f.delivery_status LIKE 'late%' THEN si.items_in_order ELSE 0 END), 
        SUM(si.items_in_order)
    ) AS late_item_pct,
    SUM(f.order_revenue) AS seller_total_revenue
FROM seller_items AS si
JOIN {{ ref('fact_orders') }} AS f 
    ON si.order_id = f.order_id
GROUP BY si.seller_id
