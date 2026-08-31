# Architecture

## Data flow

```
Kaggle (Olist CSVs, 9 files — 4 loaded so far: orders, order_items, order_reviews, customers)
        │
        │  pymongo: extract CSVs, load into MongoDB
        ▼
MongoDB: olist_landing        <- one collection per source CSV, raw landing zone
        │
        │  dlt: extract collections, load into BigQuery
        ▼
BigQuery: olist_raw          <- one table per collection, near-verbatim (bronze)
        │
        │  dbt staging + intermediate models (cast types, rename, dedupe, delay math)
        │  dbt marts/core — star schema (silver/gold)
        ▼
BigQuery: olist_warehouse    <- stg_orders, stg_order_items, stg_order_reviews,
        │                       stg_customers, int_order_delivery_stages,
        │                       dim_customer, dim_date, fact_orders
        │  dbt marts/reporting — pre-aggregated datamart
        ▼
BigQuery: olist_reporting    <- mart_delivery_kpis, mart_satisfaction_by_delivery,
        │                       mart_monthly_sales
        ▼
Streamlit dashboard  (reads ONLY olist_reporting; short, cheap, cached queries)
```

Jupyter analysis queries `olist_warehouse` / `olist_reporting` via SQLAlchemy + pandas — same
warehouse, no separate copy of the data.

**Currently implemented:** 4 of the 9 Olist tables (orders, order_items, order_reviews,
customers), enough for `fact_orders` + `dim_customer` + `dim_date` and all three business
questions from the case doc. `sellers`, `products`, `geolocation`, `order_payments`, and
`product_category_name_translation` land automatically the moment their CSV is copied into
`data/raw/` (see `ingestion/pipelines/sources/olist_csv_source.py`) — extending the star schema
with `dim_seller`/`dim_product`/`dim_geolocation` and a `fact_order_items` is the natural next
step, not yet built.

## Why 3 BigQuery datasets, not 5

Dataset count is a governance/organizational boundary in BigQuery, not a performance one — view
vs. table materialization is what affects cost, not which dataset a model lives in. Only two
boundaries here are actually load-bearing:

- **`olist_raw`** stays separate: a different tool owns it (dlt, not dbt), and nothing should
  query it directly except dbt.
- **`olist_reporting`** stays separate: the one place read access is actually restricted —
  whoever runs the dashboard only needs read access to this one dataset, not the whole
  warehouse (see "Running the dashboard" in `docs/gcp_setup.md`).

Staging, intermediate, and marts/core are all built and owned by the same dbt developers with
no reason for separate access boundaries between them, so they share one `olist_warehouse`
dataset — distinguished by naming convention (`stg_*`, `int_*`, `dim_*`/`fact_*`), same as they
already are by folder (`models/staging/`, `models/intermediate/`, `models/marts/core/` — the
folder structure didn't change, only which BigQuery dataset each folder's `+schema` config
points at; see `warehouse/olist_dbt/dbt_project.yml`).

## Why this shape

- **MongoDB is a pass-through raw landing zone, not a transformation layer.** It's included as
  a required stack component for this project. The design keeps the extra hop cheap: no
  renaming/typing/business logic happens in Mongo — that's still all in dbt — and both hops
  share one table/collection mapping so they can't drift apart.
- **pymongo owns the CSV→Mongo hop, dlt owns Mongo→BigQuery, dbt owns transform.** dlt has no
  MongoDB *destination* (only a *source*, for reading data back out) — see `ingestion/README.md`
  for the full correction. This is still deliberate ELT: raw data lands as-is (auditable,
  replayable) before any business logic is applied.
- **Star schema lives in `olist_warehouse`, not `olist_raw`.** `fact_orders` carries every
  timestamp needed for the business questions (`order_purchase_at`, `order_approved_at`,
  `order_delivered_carrier_at`, `order_delivered_customer_at`, `order_estimated_delivery_at`)
  plus derived columns (`approval_delay_days`, `seller_handling_days`, `transit_days`,
  `delivery_delay_days`, `delivery_status`) so every downstream question — delivery network
  health, satisfaction, monthly trends — is a `GROUP BY` on one fact table joined to
  `dim_customer` / `dim_date`, not a re-derivation of date math each time.
- **A separate `olist_reporting` datamart sits between the warehouse and Streamlit** so the
  dashboard never scans the full fact table. See "Datamart: reporting value and cost saving"
  below.
- **Partitioning & clustering (not yet applied, worth doing before the full 9-table build):**
  `fact_orders` should be partitioned on `order_purchase_at` (date) and clustered on
  `customer_state` (and `seller_id` once sellers are loaded). This lets both dbt incremental
  models and the dashboard's date-filtered queries prune partitions instead of scanning the
  whole table — the single biggest lever on BigQuery on-demand cost as the dataset grows.

## Datamart: reporting value and cost saving

BigQuery on-demand pricing bills by **bytes scanned per query**, not by dashboard traffic. A
Streamlit page that re-runs `SELECT ... FROM fact_orders JOIN dim_customer ...` with a
`GROUP BY` on every page load/filter change re-scans the full fact + dimension tables every
time, for every viewer. That cost (and the multi-second latency) scales with raw data size and
traffic.

The `olist_reporting` datamart pre-computes the aggregates the dashboard actually needs
(delivery KPIs by state/month, review-score-by-delivery-status buckets, monthly sales trend)
**once**, via a dbt run, as small materialized tables:

- **Cost:** `mart_delivery_kpis` (565 rows: month × state) is orders of magnitude cheaper to
  scan than joining `fact_orders` ⋈ `dim_customer` on every dashboard interaction.
- **Latency:** small tables + `st.cache_data(ttl=...)` in Streamlit mean the dashboard feels
  interactive instead of waiting on a multi-table join each time.
- **Governance:** the dashboard only ever queries `olist_reporting`, not the full warehouse —
  smaller blast radius, and dbt developers can keep refactoring `olist_warehouse` without
  breaking the dashboard's contract.

**Where to store the datamart:** as plain dbt `table` materializations in the `olist_reporting`
dataset — not views (a view re-executes the underlying join on every query, defeating the
cost-saving purpose) and not BigQuery materialized views (best suited to auto-refresh over
streaming/incremental base tables via BI Engine/Looker-style consumption; for a batch,
dbt-orchestrated pipeline, plain dbt tables give explicit control and testability). If a metric
needs to feel "live," an incremental dbt model is the right escalation — not a bigger single
query at dashboard-request time.

## Individual accounts during development

See [docs/gcp_setup.md](../gcp_setup.md). Short version: **each teammate creates their own
personal GCP project** (not a shared one — GCP bills at the project level, so a shared project
means one person's billing account absorbs everyone's usage). Only the project ID differs per
person; every dbt model and pipeline reads it from `GOOGLE_CLOUD_PROJECT` in
`config/credentials.env`, so the resulting `olist_raw` / `olist_warehouse` / `olist_reporting`
dataset names are identical across everyone's project. Exactly one project — the **submission
project** — is the team's actual deliverable that the dashboard and notebooks point to; it's
only ever updated by CI (`.github/workflows/ci.yml`), never by a manual `dbt run` from someone's
laptop.

MongoDB follows the same personal-project logic: **each teammate creates their own personal
Atlas cluster**, not a shared one — see [docs/mongodb_setup.md](../mongodb_setup.md). Since the
raw landing zone is rebuilt from the same static Kaggle CSVs every run, there's nothing to keep
in sync between people's clusters; whoever's personal Mongo feeds stage 2, the same `olist_raw`
tables land in whichever BigQuery project it's pointed at.

## Orchestration

`orchestration/` wraps both dlt hops and the dbt project as Dagster assets in one lineage graph
(`olist_mongo_landing → olist_bigquery_raw → stg_* → dim_*/fact_* → mart_*`) — useful both for
local development (the Dagster UI's asset graph doubles as the architecture diagram for the
exec deck) and as the mechanism the brief's optional "Pipeline Orchestration" criterion asks
for. There is no recurring/scheduled run: the Kaggle dataset is static, so a clock-driven
rebuild would just redo the same load against unchanging data. Instead, `.github/workflows/ci.yml`
materializes the full asset graph on push to `main` (or manual `workflow_dispatch`) — proving a
fresh environment can rebuild everything from source whenever the pipeline code changes, rather
than a self-hosted, always-on Dagster daemon. See
[orchestration/README.md](../../orchestration/README.md) for why.
