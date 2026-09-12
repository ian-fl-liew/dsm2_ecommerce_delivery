-- Delivery performance mart for the Streamlit Sunburst.
--
-- Grain: one row per top-10 revenue state + delivery outcome.
--
-- Business story:
-- Which high-revenue states are performing well or poorly
-- from a delivery perspective?

with order_delivery as (

    select
        f.order_id,
        c.customer_state,
        f.delivery_status,
        f.order_revenue

    from {{ ref('fact_orders') }} as f

    left join {{ ref('dim_customer') }} as c
        on f.customer_id = c.customer_id

),

top_states as (

    select
        customer_state,
        sum(order_revenue) as total_revenue

    from order_delivery

    group by customer_state

    order by total_revenue desc

    limit 10

)

select
    o.customer_state,
    o.delivery_status,
    count(*) as order_count,
    sum(o.order_revenue) as revenue

from order_delivery as o

inner join top_states as t
    on o.customer_state = t.customer_state

group by
    o.customer_state,
    o.delivery_status
