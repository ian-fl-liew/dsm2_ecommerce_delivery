-- Revenue and delivery risk by customer state.
--
-- Grain: one row per customer state.
--
-- Business question:
-- Which high-revenue markets have the greatest delivery risk?

with order_delivery as (

    select
        f.order_id,
        c.customer_state,
        f.delivery_status,
        f.order_revenue

    from {{ ref('fact_orders') }} as f

    inner join {{ ref('dim_customer') }} as c
        on f.customer_id = c.customer_id

    where c.customer_state is not null

)

select
    customer_state,

    count(*) as total_orders,
    sum(order_revenue) as total_revenue,

    countif(delivery_status like 'late%') as late_orders,
    sum(
        case when delivery_status like 'late%' then order_revenue else 0 end
    ) as late_revenue,

    safe_divide(
        countif(delivery_status like 'late%'),
        count(*)
    ) as late_delivery_pct,

    safe_divide(
        sum(case when delivery_status like 'late%' then order_revenue else 0 end),
        sum(order_revenue)
    ) as late_revenue_pct

from order_delivery

group by customer_state

order by total_revenue desc
