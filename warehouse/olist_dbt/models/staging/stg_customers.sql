-- 1 row per customer_id. Note: Olist mints a new customer_id per order — the
-- repeat-purchase identity is customer_unique_id. This starter keys dim_customer on
-- customer_id (order-scoped location snapshot); a repeat-customer analysis would need
-- to key on customer_unique_id instead.
select
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state
from {{ source('olist_raw', 'customers') }}
