-- Seller performance reporting mart
-- Grain: one row per seller.
--
-- Seller shipping performance is measured at order-item level:
-- shipping_limit_date vs actual carrier handoff.
--
-- Delivery performance is measured at order level and attributed
-- to sellers involved in that order.

with seller_orders as (

    select
        oi.seller_id,
        oi.order_id,
        oi.order_item_id,
        oi.price,
        oi.freight_value,
        oi.shipping_limit_date,

        d.order_delivered_carrier_at,
        d.order_delivered_customer_at,
        d.delivery_status,
        d.total_delivery_days

    from {{ ref('stg_order_items') }} as oi

    left join {{ ref('int_order_delivery_stages') }} as d
        on oi.order_id = d.order_id

),

seller_performance as (

    select
        seller_id,

        count(distinct order_id) as order_count,

        count(*) as item_count,

        sum(price) as total_revenue,

        sum(freight_value) as total_freight,

        countif(
            order_delivered_carrier_at is not null
            and shipping_limit_date is not null
        ) as shipping_item_count,

        countif(
            order_delivered_carrier_at is not null
            and shipping_limit_date is not null
            and order_delivered_carrier_at > shipping_limit_date
        ) as late_shipping_item_count,

        count(distinct case
            when delivery_status like 'late%'
            then order_id
        end) as late_delivery_order_count,

        count(distinct case
            when delivery_status is not null
            then order_id
        end) as delivered_order_count,

        avg(total_delivery_days) as avg_delivery_days

    from seller_orders

    group by seller_id

)

select
    seller_id,
    order_count,
    item_count,
    total_revenue,
    total_freight,

    shipping_item_count,
    late_shipping_item_count,

    safe_divide(
        late_shipping_item_count,
        shipping_item_count
    ) as late_shipping_pct,

    late_delivery_order_count,
    delivered_order_count,

    safe_divide(
        late_delivery_order_count,
        delivered_order_count
    ) as late_delivery_pct,

    avg_delivery_days

from seller_performance
