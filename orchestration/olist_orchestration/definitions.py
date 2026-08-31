import dagster as dg
from dagster_dbt import DbtCliResource

from .assets import dbt_project, olist_bigquery_raw, olist_dbt_assets, olist_mongo_landing
from .schedules import full_refresh_job

# No schedule: rebuilds are triggered by push to main / workflow_dispatch (see
# .github/workflows/ci.yml), not on a clock -- the source dataset is static.
#
# NOTE: olist_dbt_assets includes an asset for each dbt source node too. For the graph to
# show olist_bigquery_raw -> stg_* as one continuous lineage (rather than two disconnected
# subgraphs), confirm those dbt source asset keys line up with olist_bigquery_raw's output
# key — see dagster-dbt's docs on customizing source asset keys via DagsterDbtTranslator.
defs = dg.Definitions(
    assets=[olist_mongo_landing, olist_bigquery_raw, olist_dbt_assets],
    jobs=[full_refresh_job],
    resources={
        "dbt": DbtCliResource(project_dir=dbt_project),
    },
)
