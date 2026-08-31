#!/usr/bin/env bash
# One-time (re-runnable) local environment setup for each team member.
#
# Reads every credential from a single file, config/credentials.env (gitignored), and from
# it generates every tool-specific config file the pipeline needs (ingestion/.dlt/secrets.toml,
# ~/.dbt/profiles.yml), installs Python deps, and makes sure you're authenticated to GCP with
# your OWN Google account (see docs/gcp_setup.md).
#
# By default this also runs the full pipeline against YOUR OWN project/cluster (download data,
# ingest, build the warehouse) -- safe to do unconditionally since it's your own resources, not
# the shared submission project. Pass --skip-pipeline to only (re)generate config/deps, e.g.
# after just changing DBT_DEV_HANDLE.
#
# Usage: bash scripts/setup_local_env.sh [--skip-pipeline]
set -euo pipefail

SKIP_PIPELINE=false
if [ "${1:-}" = "--skip-pipeline" ]; then
  SKIP_PIPELINE=true
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CREDS_FILE="$REPO_ROOT/config/credentials.env"
CREDS_EXAMPLE="$REPO_ROOT/config/credentials.env.example"

echo "== Olist project: local environment setup =="
echo "Repo: $REPO_ROOT"
echo

echo "-- 1/9: credentials folder + template --"
mkdir -p "$REPO_ROOT/config"
if [ ! -f "$CREDS_EXAMPLE" ]; then
  # Defensive: recreate the tracked template if it's ever missing (partial checkout, etc.)
  cat > "$CREDS_EXAMPLE" <<'EXAMPLE'
# Copy this file to config/credentials.env and fill in your own values.
# credentials.env is gitignored -- this .example is the tracked template.

# Your OWN personal GCP project (see docs/gcp_setup.md) -- NOT the team's submission project.
# BigQuery access comes from `gcloud auth login` / `gcloud auth application-default login`
# with YOUR Google account, not a key stored here.
GOOGLE_CLOUD_PROJECT=olist-dsai-YOUR_NAME

# Used to generate ~/.dbt/profiles.yml's per-developer dev dataset (dbt_dev_<this>).
# Defaults to your OS username in the setup script if left blank.
DBT_DEV_HANDLE=

# Kaggle -> Settings -> API -> Create New Token (kaggle.com/settings)
KAGGLE_USERNAME=
KAGGLE_KEY=

# MongoDB Atlas connection string for YOUR database user (see docs/mongodb_setup.md)
MONGODB_CONNECTION_URL=
EXAMPLE
  echo "Recreated missing template -> config/credentials.env.example"
fi

if [ ! -f "$CREDS_FILE" ]; then
  cp "$CREDS_EXAMPLE" "$CREDS_FILE"
  echo "Created config/credentials.env from the template -- it's currently empty."
  echo "Edit it now with your Kaggle + MongoDB values (see docs/gcp_setup.md and"
  echo "docs/mongodb_setup.md for where those come from), then re-run this script."
  exit 1
fi
echo "OK -> config/credentials.env exists"
echo

set -a
# shellcheck disable=SC1090
source "$CREDS_FILE"
set +a

if [ "$GOOGLE_CLOUD_PROJECT" = "olist-dsai-YOUR_NAME" ]; then
  echo "config/credentials.env still has the placeholder GOOGLE_CLOUD_PROJECT."
  echo "Set it to YOUR OWN GCP project (see docs/gcp_setup.md) -- never the team's"
  echo "submission project (ntu-bigdata-project) -- then re-run this script."
  exit 1
fi

missing=()
for var in GOOGLE_CLOUD_PROJECT KAGGLE_USERNAME KAGGLE_KEY MONGODB_CONNECTION_URL; do
  if [ -z "${!var:-}" ]; then
    missing+=("$var")
  fi
done
if [ ${#missing[@]} -gt 0 ]; then
  echo "config/credentials.env is missing: ${missing[*]}"
  echo "Fill those in and re-run."
  exit 1
fi
DBT_DEV_HANDLE="${DBT_DEV_HANDLE:-$(whoami)}"

echo "-- 2/9: Python virtual environment (.venv) + dependencies --"
if [ ! -d "$REPO_ROOT/.venv" ]; then
  python3 -m venv "$REPO_ROOT/.venv"
  echo "Created .venv"
fi
VENV_PIP="$REPO_ROOT/.venv/bin/pip"
"$VENV_PIP" install -q --upgrade pip

# Auto-discover every requirements.txt in the repo rather than hardcoding each one here --
# a new component's requirements.txt (e.g. analysis/) is picked up automatically next run,
# no need to remember to wire it in. orchestration/ is excluded: dagster-dbt doesn't yet have
# a Python 3.14-compatible release (pins to dagster==1.12.8, which itself requires <3.14) --
# see orchestration/README.md for its own separate-environment setup.
while IFS= read -r req_file; do
  echo "  installing $req_file"
  "$VENV_PIP" install -q -r "$req_file"
done < <(find "$REPO_ROOT" \
  \( -path "$REPO_ROOT/.venv" -o -path "$REPO_ROOT/project_brief" \
     -o -path "$REPO_ROOT/orchestration" \
     -o -name "dbt_packages" -o -name "node_modules" -o -name ".git" \) -prune -o \
  -name "requirements.txt" -print | sort)

"$VENV_PIP" install -q dbt-bigquery kagglehub
echo "OK -> .venv (activate with: source .venv/bin/activate)"
echo

echo "-- 3/9: Google Cloud auth (your own account, not a shared key) --"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q .; then
  echo "No active gcloud login -- opening browser (sign in with YOUR Google account)."
  gcloud auth login
fi
if [ ! -f "$HOME/.config/gcloud/application_default_credentials.json" ]; then
  echo "No Application Default Credentials -- opening browser."
  gcloud auth application-default login
fi
gcloud config set project "$GOOGLE_CLOUD_PROJECT" --quiet
echo "OK ($(gcloud config get-value account 2>/dev/null) -> $GOOGLE_CLOUD_PROJECT)"
echo

echo "-- 4/9: dlt secrets (ingestion/.dlt/secrets.toml) --"
mkdir -p "$REPO_ROOT/ingestion/.dlt"
cat > "$REPO_ROOT/ingestion/.dlt/secrets.toml" <<TOML
# Generated by scripts/setup_local_env.sh from config/credentials.env. Do not hand-edit --
# edit credentials.env and re-run the script instead.

[destination.mongodb]
connection_url = "$MONGODB_CONNECTION_URL"

[sources.mongodb]
connection_url = "$MONGODB_CONNECTION_URL"

[destination.bigquery]
location = "US"
TOML
echo "OK -> ingestion/.dlt/secrets.toml"
echo

echo "-- 5/9: dbt profile (~/.dbt/profiles.yml) --"
mkdir -p "$HOME/.dbt"
cat > "$HOME/.dbt/profiles.yml" <<YAML
# Generated by scripts/setup_local_env.sh. dev = your personal schema, safe to iterate in;
# prod = your own project's "finished" copy (dbt run -t prod) -- NOT the team's shared
# submission project, which only CI ever writes to. See docs/gcp_setup.md.
olist_dbt:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: oauth
      project: $GOOGLE_CLOUD_PROJECT
      dataset: dbt_dev_${DBT_DEV_HANDLE}
      threads: 4
      location: US
    prod:
      type: bigquery
      method: oauth
      project: $GOOGLE_CLOUD_PROJECT
      dataset: olist
      threads: 4
      location: US
YAML
echo "OK -> ~/.dbt/profiles.yml (dev dataset: dbt_dev_${DBT_DEV_HANDLE})"
echo

echo "-- 6/9: Kaggle auth --"
echo "kagglehub/kaggle CLI read KAGGLE_USERNAME / KAGGLE_KEY directly from the"
echo "environment -- already set by sourcing credentials.env above (also exported to this"
echo "script's own environment, so steps 7-9 below pick them up automatically)."
echo

VENV_PY="$REPO_ROOT/.venv/bin/python"

if [ "$SKIP_PIPELINE" = true ]; then
  echo "-- 7-9/9: skipped (--skip-pipeline) --"
  echo
  cat <<'NEXT'
== Config/deps refreshed. Pipeline steps were skipped. Run manually when ready: ==
  source .venv/bin/activate
  python scripts/download_dataset.py
  python ingestion/pipelines/csv_to_mongo_pipeline.py data/raw
  python ingestion/pipelines/mongo_to_bigquery_pipeline.py
  cd warehouse/olist_dbt && dbt deps && dbt run && dbt test
  cd dashboard && streamlit run app.py
NEXT
  exit 0
fi

echo "-- 7/9: download the Kaggle dataset --"
"$VENV_PY" "$REPO_ROOT/scripts/download_dataset.py"
echo

echo "-- 8/9: ingestion pipeline (CSV -> your MongoDB -> your BigQuery olist_raw) --"
"$VENV_PY" "$REPO_ROOT/ingestion/pipelines/csv_to_mongo_pipeline.py" "$REPO_ROOT/data/raw"
"$VENV_PY" "$REPO_ROOT/ingestion/pipelines/mongo_to_bigquery_pipeline.py"
echo

echo "-- 9/9: build the warehouse + datamart (dev target, your own project) --"
VENV_DBT="$REPO_ROOT/.venv/bin/dbt"
(cd "$REPO_ROOT/warehouse/olist_dbt" && "$VENV_DBT" deps && "$VENV_DBT" run && "$VENV_DBT" test)
echo

cat <<'NEXT'
== Setup complete. Full pipeline ran against YOUR OWN project/cluster. ==
Next step -- run the dashboard or notebooks:
  source .venv/bin/activate
  cd dashboard && streamlit run app.py
(For analysis/*.ipynb in VS Code, see analysis/README.md for picking the right kernel.)

Re-run with --skip-pipeline next time if you only changed config, not the data.
NEXT
