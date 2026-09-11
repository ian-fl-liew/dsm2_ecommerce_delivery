-- fact_orders is item grain, and every order-level measure on it (revenue, freight, the
-- delivery-stage days, review score) repeats across the order's items. Five reporting
-- marts rely on is_order_header_row marking EXACTLY one row per order to collapse back to
-- order grain before aggregating. If that invariant ever breaks, those marts silently
-- over- or under-count instead of failing, so assert it here.
select
    order_id,
    countif(is_order_header_row) as header_row_count
from {{ ref('fact_orders') }}
group by order_id
having countif(is_order_header_row) != 1
