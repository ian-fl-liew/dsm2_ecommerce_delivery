-- 1 row per order line item.
select
    order_id,
    order_item_id,
    product_id,
    seller_id,
    shipping_limit_date,
    price,
    freight_value
from {{ source('olist_raw', 'order_items') }}
