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
where avg_review_score is not null
group by delivery_status
