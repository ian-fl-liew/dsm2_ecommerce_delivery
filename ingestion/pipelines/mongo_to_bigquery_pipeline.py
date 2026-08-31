"""Stage 2: load the raw Olist collections out of MongoDB into BigQuery `olist_raw`.

Run after csv_to_mongo_pipeline.py has populated the `olist_landing` MongoDB database:
    python ingestion/pipelines/mongo_to_bigquery_pipeline.py

Uses dlt's MongoDB verified source, vendored into sources/mongodb/ (added via
`dlt init mongodb bigquery` — verified sources aren't pip-installable, they're copied
into your own project by the dlt CLI, which is why this lives in-repo rather than as a
package import). Loads exactly the collections that exist in TABLE_FILES /
sources/olist_csv_source.py, so stage 1 and stage 2 can't drift out of sync.
"""
import os
from pathlib import Path

# dlt resolves .dlt/config.toml + .dlt/secrets.toml relative to DLT_PROJECT_DIR (falling
# back to cwd if unset) -- set explicitly so this pipeline works regardless of the caller's
# cwd (plain CLI run, Dagster asset, CI step).
os.environ.setdefault("DLT_PROJECT_DIR", str(Path(__file__).parents[1]))

import dlt  # noqa: E402

from csv_to_mongo_pipeline import DATABASE_NAME  # noqa: E402
from sources.mongodb import mongodb  # noqa: E402
from sources.olist_csv_source import TABLE_FILES  # noqa: E402

PIPELINE_NAME = "olist_bigquery_raw"
DATASET_NAME = "olist_raw"


def build_pipeline() -> dlt.Pipeline:
    return dlt.pipeline(
        pipeline_name=PIPELINE_NAME,
        destination="bigquery",
        dataset_name=DATASET_NAME,
    )


def run():
    pipeline = build_pipeline()
    source = mongodb(database=DATABASE_NAME, collection_names=list(TABLE_FILES.keys()))
    load_info = pipeline.run(source, write_disposition="replace")
    print(load_info)
    return load_info


if __name__ == "__main__":
    run()
