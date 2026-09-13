-- Order grain. Classifies each order's shape and seller-to-customer distance band, shared by
-- mart_transit_drivers and mart_transit_unclassified so both read one definition.
--
-- unclassified_reason is null for classified orders; otherwise it says why no handoff
-- could be measured.

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
        order_status,
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

with_handoff as (
    select
        h.*,
        s.seller_city,
        s.seller_state,
        c.customer_city,
        c.customer_state,
        timestamp_diff(
            h.order_delivered_carrier_at, sla.last_shipping_limit_at, hour
        ) / 24.0 as carrier_handoff_vs_limit_days
    from order_header as h
    left join order_sla as sla on h.order_id = sla.order_id
    left join seller_rank as sr on h.order_id = sr.order_id and sr.revenue_rank = 1
    left join {{ ref('dim_seller') }} as s on sr.seller_id = s.seller_id
    left join {{ ref('dim_customer') }} as c on h.customer_id = c.customer_id
),

reasoned as (
    select
        *,
        case
            when distinct_seller_count = 0 then 'no_items_on_order'
            when order_approved_at is null and order_delivered_carrier_at is null
                then 'never_approved_or_shipped'
            when order_approved_at is null then 'approval_timestamp_missing'
            when order_delivered_carrier_at is null then 'never_handed_to_carrier'
        end as unclassified_reason
    from with_handoff
)

select
    order_id,
    order_status,
    delivery_status,
    transit_days,
    total_delivery_days,
    delivery_delay_days,
    seller_handling_days,
    carrier_handoff_vs_limit_days,
    unclassified_reason,

    case
        when unclassified_reason is not null then 'unclassified'
        when distinct_seller_count > 1 then 'multi_seller'
        when seller_handling_days > {{ slow_handoff_days }}
            and carrier_handoff_vs_limit_days > {{ sla_breach_days }}
            then 'single_seller_slow_handoff'
        else 'single_seller_normal_handoff'
    end as order_shape,

    case
        when seller_state is null or customer_state is null then '4. unknown'
        when lower(seller_city) = lower(customer_city)
            and seller_state = customer_state then '1. same_city'
        when seller_state = customer_state then '2. same_state'
        else '3. cross_state'
    end as distance_band

from reasoned
