-- Delivery-journey delay math per order (business case doc, "4. Is the seller slow, or
-- is logistics slow?"). seller_handling_days is order-level here (no dim_seller yet in
-- this starter, since olist_sellers_dataset isn't loaded) -- it's the elapsed time
-- between approval and carrier handoff, regardless of which seller(s) fulfilled it.
with orders as (
    select * from {{ ref('stg_orders') }}
)

select
    order_id,
    customer_id,
    order_status,
    order_purchase_at,
    order_approved_at,
    order_delivered_carrier_at,
    order_delivered_customer_at,
    order_estimated_delivery_at,

    timestamp_diff(order_approved_at, order_purchase_at, hour) / 24.0
        as approval_delay_days,
    timestamp_diff(order_delivered_carrier_at, order_approved_at, hour) / 24.0
        as seller_handling_days,
    timestamp_diff(order_delivered_customer_at, order_delivered_carrier_at, hour) / 24.0
        as transit_days,
    timestamp_diff(order_delivered_customer_at, order_purchase_at, hour) / 24.0
        as total_delivery_days,
    timestamp_diff(order_delivered_customer_at, order_estimated_delivery_at, hour) / 24.0
        as delivery_delay_days,

    case
        when order_delivered_customer_at is null then 'not_delivered'
        when order_delivered_customer_at <= order_estimated_delivery_at then
            case
                when timestamp_diff(order_estimated_delivery_at, order_delivered_customer_at, day) >= 1
                    then 'early'
                else 'on_time'
            end
        else
            case
                when timestamp_diff(order_delivered_customer_at, order_estimated_delivery_at, day) <= 3 then 'late_1_3_days'
                when timestamp_diff(order_delivered_customer_at, order_estimated_delivery_at, day) <= 7 then 'late_4_7_days'
                else 'late_8_plus_days'
            end
    end as delivery_status

from orders
