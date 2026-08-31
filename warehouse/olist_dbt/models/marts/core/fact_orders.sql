-- Grain: 1 row per order. Joins in the review score (secondary business goal) and an
-- order-level rollup of items (revenue/freight/item count) so downstream reporting
-- never has to re-join order_items itself.
with delivery as (
    select * from {{ ref('int_order_delivery_stages') }}
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
        sum(price) as order_revenue,
        sum(freight_value) as order_freight
    from {{ ref('stg_order_items') }}
    group by order_id
)

select
    delivery.order_id,
    delivery.customer_id,
    delivery.order_status,
    delivery.order_purchase_at,
    delivery.order_approved_at,
    delivery.order_delivered_carrier_at,
    delivery.order_delivered_customer_at,
    delivery.order_estimated_delivery_at,
    delivery.approval_delay_days,
    delivery.seller_handling_days,
    delivery.transit_days,
    delivery.total_delivery_days,
    delivery.delivery_delay_days,
    delivery.delivery_status,
    coalesce(items.item_count, 0) as item_count,
    coalesce(items.order_revenue, 0.0) as order_revenue,
    coalesce(items.order_freight, 0.0) as order_freight,
    review.avg_review_score,
    review.review_count
from delivery
left join review_by_order as review on delivery.order_id = review.order_id
left join items_by_order as items on delivery.order_id = items.order_id
