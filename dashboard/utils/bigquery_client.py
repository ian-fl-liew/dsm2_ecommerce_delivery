"""Read-only BigQuery client for the Streamlit dashboard.

Queries only the `olist_reporting` datamart dataset (see docs/architecture/README.md) —
never the raw or marts.core datasets — and caches results so repeated user interaction
doesn't re-bill the same query.

Project comes from GOOGLE_CLOUD_PROJECT (set in config/credentials.env), same as every
other tool in the repo -- never hardcode a project ID here. Defaults to the team's
submission project (see "The submission project" in docs/gcp_setup.md); a teammate can
still point their local dashboard at their own personal project to verify a change
end-to-end before it's merged, just by setting GOOGLE_CLOUD_PROJECT to their own project ID.
"""
import os

import streamlit as st
from google.cloud import bigquery

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "ntu-bigdata-project")
REPORTING_DATASET = "olist_reporting"


@st.cache_resource
def get_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)


@st.cache_data(ttl=3600)
def query(sql: str):
    return get_client().query(sql).to_dataframe()
