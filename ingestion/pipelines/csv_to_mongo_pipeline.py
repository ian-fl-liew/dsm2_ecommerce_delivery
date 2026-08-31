"""Stage 1: load the Olist Kaggle CSVs into MongoDB as the raw landing zone.

Run after downloading the dataset (see scripts/download_dataset.py):
    python ingestion/pipelines/csv_to_mongo_pipeline.py /path/to/downloaded/dataset

NOTE: this stage uses plain pymongo, not dlt. dlt does not ship a MongoDB *destination*
(only a MongoDB *source*, for reading data back out — see mongo_to_bigquery_pipeline.py
and sources/mongodb/, dlt's own verified source, used for stage 2). Writing flat CSV rows
into a document store doesn't need an ELT framework anyway; a bulk insert_many per
collection is the idiomatic pymongo way to do it.

One collection per source CSV, written as-is (no renaming/typing/business logic —
that still happens later, in dbt). Mongo connection comes from
ingestion/.dlt/secrets.toml (destination.mongodb.connection_url) — see
docs/mongodb_setup.md for your own personal Atlas cluster setup.
"""
import sys
import tomllib
from pathlib import Path

import pandas as pd
from pymongo import MongoClient

from sources.olist_csv_source import TABLE_FILES

DATABASE_NAME = "olist_landing"
SECRETS_PATH = Path(__file__).parents[1] / ".dlt" / "secrets.toml"


def _connection_url() -> str:
    secrets = tomllib.loads(SECRETS_PATH.read_text())
    return secrets["destination"]["mongodb"]["connection_url"]


def run(data_dir: str = "data/raw") -> dict:
    data_path = Path(data_dir)
    client = MongoClient(_connection_url())
    db = client[DATABASE_NAME]

    counts = {}
    for table_name, filename in TABLE_FILES.items():
        csv_path = data_path / filename
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path)
        collection = db[table_name]
        # drop(), not delete_many({}): replace semantics matching dlt's write_disposition=
        # "replace", but delete_many() leaves fragmented space that Atlas's free M0 tier can't
        # reclaim (no `compact` command on shared tiers) -- repeated re-runs will eventually
        # blow the 512MB quota even though the logical dataset size never changes. drop()
        # actually deallocates storage, and being a metadata op rather than a write, it isn't
        # blocked even if the cluster is currently over quota.
        collection.drop()
        records = df.to_dict("records")
        if records:
            collection.insert_many(records)
        counts[table_name] = len(records)
        print(f"{table_name}: {len(records)} documents -> {DATABASE_NAME}.{table_name}")

    return counts


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "data/raw")
