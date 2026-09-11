-- Monthly sales trend (brief's "Data Analysis with Python" -> Monthly sales trends).

select
    date_trunc(cast(order_purchase_at as date), month) as order_month,
    count(distinct order_id) as order_count,
    sum(order_revenue) as total_revenue,
    sum(order_freight) as total_freight,
    safe_divide(sum(order_revenue), count(distinct order_id)) as avg_order_value
from {{ ref('fact_orders') }}
where is_order_header_row
group by 1
order by 1
