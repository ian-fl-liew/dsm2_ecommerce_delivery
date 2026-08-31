# Core marts — star schema

- `dim_customer`, `dim_seller`, `dim_product`, `dim_date`, `dim_geolocation`
- `fact_orders` (grain: one row per order) — carries every delivery-journey timestamp and the
  derived delay/status columns (see docs/architecture/README.md)
- `fact_order_items` (grain: one row per order line item) — links to `dim_product`/`dim_seller`
  for price/freight and product-characteristic questions (size/weight vs. delivery time)

This is the layer the 3 dbt/BigQuery teammates own jointly. Keep it normalized/queryable, not
pre-aggregated — aggregation belongs in `marts/reporting`.
