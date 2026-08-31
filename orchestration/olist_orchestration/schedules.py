import dagster as dg

# No ScheduleDefinition: the Kaggle dataset is a static one-time export, so there's nothing
# to refresh on a clock. This job is triggered manually (`dagster asset materialize`) or by
# .github/workflows/ci.yml on push to main -- see orchestration/README.md.
full_refresh_job = dg.define_asset_job(
    name="olist_full_refresh",
    selection=dg.AssetSelection.all(),
    description="Ingest Olist CSVs into olist_raw, then run dbt build "
    "(staging -> marts -> reporting) in dependency order.",
)
