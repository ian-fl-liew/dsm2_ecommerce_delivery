-- 1 row per order. Drops the MongoDB-hop artifact columns (_id, _dlt_*) picked up
-- when the raw data passed through the Mongo landing zone.
select
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp as order_purchase_at,
    order_approved_at,
    order_delivered_carrier_date as order_delivered_carrier_at,
    order_delivered_customer_date as order_delivered_customer_at,
    order_estimated_delivery_date as order_estimated_delivery_at
from {{ source('olist_raw', 'orders') }}
