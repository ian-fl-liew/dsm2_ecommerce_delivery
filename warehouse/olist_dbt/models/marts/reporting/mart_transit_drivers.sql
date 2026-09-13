-- What actually drives transit time (carrier handoff -> customer)?
--
-- order_shape values, each named for what is measured:
--
--   multi_seller
--   single_seller_slow_handoff
--   single_seller_normal_handoff
--   unclassified
--       No items on the order, or approval/carrier timestamps missing.
--       Broken down by reason in mart_transit_unclassified.
--
-- Compare order_shape WITHIN a distance_band. Comparing across bands mostly measures
-- Brazilian geography.
--
-- Classification lives in int_order_transit_shape.

select
    order_shape,
    distance_band,
    count(*) as order_count,
    safe_divide(count(*), sum(count(*)) over ()) as pct_of_orders,

    -- transit_days is null until an order is actually delivered, so these averages run
    -- over delivered orders only; delivered_order_count is their true denominator.
    countif(transit_days is not null) as delivered_order_count,
    avg(transit_days) as avg_transit_days,
    approx_quantiles(transit_days, 100)[offset(50)] as median_transit_days,
    approx_quantiles(transit_days, 100)[offset(90)] as p90_transit_days,

    avg(seller_handling_days) as avg_seller_handling_days,
    avg(total_delivery_days) as avg_total_delivery_days,
    avg(delivery_delay_days) as avg_delivery_delay_days,
    avg(carrier_handoff_vs_limit_days) as avg_carrier_handoff_vs_limit_days,
    safe_divide(
        countif(delivery_status like 'late%'),
        countif(delivery_status != 'not_delivered')
    ) as late_pct

from {{ ref('int_order_transit_shape') }}
group by order_shape, distance_band
order by order_shape, distance_band
