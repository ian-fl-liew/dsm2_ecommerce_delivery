-- Why orders fall into order_shape = 'unclassified' in mart_transit_drivers.
-- Grain: 1 row per (distance_band, unclassified_reason, order_status).
--
-- Most unclassified orders never shipped, so they have no transit_days and contribute
-- nothing to the transit averages. delivered_order_count shows how few actually do.

select
    distance_band,
    unclassified_reason,
    order_status,
    count(*) as order_count,
    countif(transit_days is not null) as delivered_order_count,
    avg(transit_days) as avg_transit_days
from {{ ref('int_order_transit_shape') }}
where order_shape = 'unclassified'
group by distance_band, unclassified_reason, order_status
order by distance_band, unclassified_reason, order_count desc
