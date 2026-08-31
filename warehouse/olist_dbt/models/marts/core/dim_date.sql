-- Date spine covering the full order history range, for joining fact_orders on any
-- of its date columns and for monthly rollups in the reporting datamart.
with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2016-01-01' as date)",
        end_date="cast('2019-01-01' as date)"
    ) }}
)

select
    date_day as date_key,
    extract(year from date_day) as year,
    extract(month from date_day) as month,
    format_date('%Y-%m', date_day) as year_month,
    format_date('%B', date_day) as month_name,
    extract(day from date_day) as day_of_month,
    extract(dayofweek from date_day) as day_of_week,
    extract(dayofweek from date_day) in (1, 7) as is_weekend
from spine
