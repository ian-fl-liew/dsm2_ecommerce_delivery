-- Business Question 7: Which sellers are both high-volume AND poor performers?
-- Grain: 1 row per seller.
--
-- Reads fact_orders directly now that it carries seller_id at item grain, so the old
-- join back to stg_order_items is gone along with its fan-out risk.
--

select
    f.seller_id,
    s.seller_city,
    s.seller_state,
    count(*) as seller_item_count,
    count(distinct f.order_id) as seller_order_count,
    countif(f.delivery_status = 'not_delivered') as not_delivered_item_count,
    countif(f.delivery_status in ('early', 'on_time')) as on_time_item_count,
    countif(f.delivery_status like 'late%') as late_item_count,
    safe_divide(
        countif(f.delivery_status like 'late%'),
        count(*)
    ) as late_item_pct,
    sum(f.item_price) as seller_total_revenue
from {{ ref('fact_orders') }} as f
join {{ ref('dim_seller') }} as s
    on f.seller_id = s.seller_id
group by f.seller_id, s.seller_city, s.seller_state
