"""Wraps the two-stage dlt ingestion (ingestion/pipelines/) as Dagster assets, so both
hops show up in the same lineage graph as the dbt models downstream of them:
olist_mongo_landing -> olist_bigquery_raw -> stg_* -> dim_*/fact_* -> mart_*.

Uses plain @dg.asset (not the dlt_assets decorator) so the dependency between the two
pipeline stages is explicit and simple, rather than relying on cross-pipeline asset-key
matching in dagster-embedded-elt.
"""
import sys
from pathlib import Path

import dagster as dg

REPO_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(REPO_ROOT / "ingestion" / "pipelines"))

import csv_to_mongo_pipeline  # noqa: E402
import mongo_to_bigquery_pipeline  # noqa: E402


@dg.asset(group_name="ingestion", description="Kaggle CSVs -> MongoDB olist_landing")
def olist_mongo_landing() -> dg.MaterializeResult:
    load_info = csv_to_mongo_pipeline.run(data_dir=str(REPO_ROOT / "data" / "raw"))
    return dg.MaterializeResult(metadata={"load_info": dg.MetadataValue.text(str(load_info))})


@dg.asset(
    deps=[olist_mongo_landing],
    group_name="ingestion",
    description="MongoDB olist_landing -> BigQuery olist_raw",
)
def olist_bigquery_raw() -> dg.MaterializeResult:
    load_info = mongo_to_bigquery_pipeline.run()
    return dg.MaterializeResult(metadata={"load_info": dg.MetadataValue.text(str(load_info))})
