-- Grain: 1 row per order line item (order_id + order_item_id).
--
-- Deepened from the old order grain so seller_id and product_id sit at their natural
-- level. An order can span several sellers, which the previous order-grain version could
-- not represent at all.
--
-- READ THIS BEFORE AGGREGATING -- two kinds of measure live side by side here:
--
--   Item-level (safe to SUM across every row):
--     item_price, item_freight
--
--   Order-level, REPEATED on every item of the order (SUM will over-count):
--     approval_delay_days, seller_handling_days, transit_days, total_delivery_days,
--     delivery_delay_days, delivery_status, item_count, order_revenue, order_freight,
--     avg_review_score, review_count
--
-- Olist stamps the carrier handoff and the customer delivery ONCE PER ORDER, so the
-- delivery-stage metrics are order facts by nature, not item facts. To aggregate any of
-- them correctly, filter `where is_order_header_row` -- that flag marks exactly one row
-- per order, so the filtered set is the old order grain, 1:1.
--
-- Itemless orders (775 of them in the Olist extract -- mostly cancelled/unavailable) are
-- preserved via a LEFT join, with null order_item_id/seller_id/product_id. That keeps the
-- order-level row count whole at 99,441 so the delivery KPI marts stay comparable to the
-- order-grain version.
with delivery as (
    select * from {{ ref('int_order_delivery_stages') }}
),

items as (
    select * from {{ ref('stg_order_items') }}
),

review_by_order as (
    select
        order_id,
        avg(review_score) as avg_review_score,
        count(*) as review_count
    from {{ ref('stg_order_reviews') }}
    group by order_id
),

items_by_order as (
    select
        order_id,
        count(*) as item_count,
        count(distinct seller_id) as distinct_seller_count,
        sum(price) as order_revenue,
        sum(freight_value) as order_freight
    from items
    group by order_id
)

select
    -- grain
    delivery.order_id,
    items.order_item_id,

    -- dimension keys
    delivery.customer_id,
    items.seller_id,
    items.product_id,

    -- exactly one true row per order: filter on this to aggregate order-level measures
    row_number() over (
        partition by delivery.order_id
        order by items.order_item_id
    ) = 1 as is_order_header_row,

    delivery.order_status,
    delivery.order_purchase_at,
    delivery.order_approved_at,
    delivery.order_delivered_carrier_at,
    delivery.order_delivered_customer_at,
    delivery.order_estimated_delivery_at,

    -- item-level measures
    items.shipping_limit_date as item_shipping_limit_at,
    items.price as item_price,
    items.freight_value as item_freight,

    -- order-level delivery stages, repeated across the order's items
    delivery.approval_delay_days,
    delivery.seller_handling_days,
    delivery.transit_days,
    delivery.total_delivery_days,
    delivery.delivery_delay_days,
    delivery.delivery_status,

    -- order-level rollups, repeated across the order's items
    coalesce(items_by_order.item_count, 0) as item_count,
    coalesce(items_by_order.distinct_seller_count, 0) as distinct_seller_count,
    coalesce(items_by_order.order_revenue, 0.0) as order_revenue,
    coalesce(items_by_order.order_freight, 0.0) as order_freight,
    review.avg_review_score,
    review.review_count

from delivery
left join items on delivery.order_id = items.order_id
left join review_by_order as review on delivery.order_id = review.order_id
left join items_by_order on delivery.order_id = items_by_order.order_id
