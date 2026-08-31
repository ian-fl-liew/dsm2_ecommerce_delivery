-- 1 row per review. An order can carry more than one review; averaged onto
-- fact_orders in the intermediate layer.
select
    review_id,
    order_id,
    review_score,
    review_creation_date,
    review_answer_timestamp
from {{ source('olist_raw', 'order_reviews') }}
