-- What actually drives transit time (carrier handoff -> customer)?
--
-- order_shape values, each named for what is measured:
--
--   multi_seller
--   single_seller_slow_handoff
--   single_seller_normal_handoff
--   unclassified
--       No items on the order, or approval/carrier timestamps missing.
--
-- Compare order_shape WITHIN a distance_band. Comparing across bands mostly measures
-- Brazilian geography.

{% set slow_handoff_days = var('slow_handoff_days', 5) %}
{% set sla_breach_days = var('sla_breach_days', 0) %}

with order_items as (
    select * from {{ ref('fact_orders') }}
    where seller_id is not null
),

order_header as (
    select
        order_id,
        customer_id,
        distinct_seller_count,
        order_approved_at,
        order_delivered_carrier_at,
        seller_handling_days,
        transit_days,
        total_delivery_days,
        delivery_delay_days,
        delivery_status
    from {{ ref('fact_orders') }}
    where is_order_header_row
),

-- Latest SLA across the order's items: the deadline the whole shipment had to clear.
-- TIMESTAMP() guards against shipping_limit_date landing as DATETIME from the Mongo hop.
order_sla as (
    select
        order_id,
        max(timestamp(item_shipping_limit_at)) as last_shipping_limit_at
    from order_items
    group by order_id
),

-- The highest-revenue seller represents the order's geography. seller_id breaks ties so
-- the pick is stable across runs.
seller_rank as (
    select
        order_id,
        seller_id,
        row_number() over (
            partition by order_id
            order by sum(item_price) desc, seller_id
        ) as revenue_rank
    from order_items
    group by order_id, seller_id
),

classified as (
    select
        h.order_id,
        h.transit_days,
        h.total_delivery_days,
        h.delivery_delay_days,
        h.delivery_status,
        h.seller_handling_days,

        timestamp_diff(
            h.order_delivered_carrier_at, sla.last_shipping_limit_at, hour
        ) / 24.0 as carrier_handoff_vs_limit_days,

        case
            when h.distinct_seller_count = 0 then 'unclassified'
            when h.order_approved_at is null
                or h.order_delivered_carrier_at is null then 'unclassified'
            when h.distinct_seller_count > 1 then 'multi_seller'
            when h.seller_handling_days > {{ slow_handoff_days }}
                and timestamp_diff(
                    h.order_delivered_carrier_at, sla.last_shipping_limit_at, hour
                ) / 24.0 > {{ sla_breach_days }}
                then 'single_seller_slow_handoff'
            else 'single_seller_normal_handoff'
        end as order_shape,

        case
            when s.seller_state is null or c.customer_state is null then '4. unknown'
            when lower(s.seller_city) = lower(c.customer_city)
                and s.seller_state = c.customer_state then '1. same_city'
            when s.seller_state = c.customer_state then '2. same_state'
            else '3. cross_state'
        end as distance_band

    from order_header as h
    left join order_sla as sla on h.order_id = sla.order_id
    left join seller_rank as sr on h.order_id = sr.order_id and sr.revenue_rank = 1
    left join {{ ref('dim_seller') }} as s on sr.seller_id = s.seller_id
    left join {{ ref('dim_customer') }} as c on h.customer_id = c.customer_id
)

select
    order_shape,
    distance_band,
    count(*) as order_count,
    safe_divide(count(*), sum(count(*)) over ()) as pct_of_orders,

    -- transit_days is null until an order is actually delivered, so these averages run
    -- over delivered orders only; delivered_order_count is their true denominator.
    countif(transit_days is not null) as delivered_order_count,
    avg(transit_days) as avg_transit_days,
    approx_quantiles(transit_days, 100)[offset(50)] as median_transit_days,
    approx_quantiles(transit_days, 100)[offset(90)] as p90_transit_days,

    avg(seller_handling_days) as avg_seller_handling_days,
    avg(total_delivery_days) as avg_total_delivery_days,
    avg(delivery_delay_days) as avg_delivery_delay_days,
    avg(carrier_handoff_vs_limit_days) as avg_carrier_handoff_vs_limit_days,
    safe_divide(
        countif(delivery_status like 'late%'),
        countif(delivery_status != 'not_delivered')
    ) as late_pct

from classified
group by order_shape, distance_band
order by order_shape, distance_band
