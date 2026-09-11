-- Business Question 3: does delivery performance relate to customer satisfaction?
-- One row per delivery_status bucket -- directly answers "avg review score by how
-- late the order was".
select
    delivery_status,
    count(*) as order_count,
    avg(avg_review_score) as avg_review_score,
    avg(total_delivery_days) as avg_delivery_days,
    avg(delivery_delay_days) as avg_delivery_delay_days
from {{ ref('fact_orders') }}
-- fact_orders is item grain; review score and delivery days are order-level, so
-- is_order_header_row keeps each order weighted once rather than once per item.
where avg_review_score is not null
  and is_order_header_row
group by delivery_status
