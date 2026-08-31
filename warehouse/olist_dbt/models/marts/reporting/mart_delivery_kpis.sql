-- Business Question 2: how well is the delivery network performing?
-- One row per (month, customer_state). Small, pre-aggregated -- this is what the
-- Streamlit dashboard queries, never fact_orders directly.
select
    date_trunc(cast(f.order_purchase_at as date), month) as order_month,
    c.customer_state,
    count(*) as order_count,
    countif(f.delivery_status = 'not_delivered') as not_delivered_count,
    countif(f.delivery_status in ('early', 'on_time')) as on_time_count,
    countif(f.delivery_status like 'late%') as late_count,
    safe_divide(countif(f.delivery_status like 'late%'), count(*)) as late_pct,
    avg(f.total_delivery_days) as avg_delivery_days,
    avg(f.seller_handling_days) as avg_seller_handling_days,
    avg(f.transit_days) as avg_transit_days,
    sum(f.order_revenue) as total_revenue
from {{ ref('fact_orders') }} as f
join {{ ref('dim_customer') }} as c on f.customer_id = c.customer_id
group by 1, 2
