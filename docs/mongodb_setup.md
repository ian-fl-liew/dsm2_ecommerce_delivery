# MongoDB setup

MongoDB is a required raw staging layer for learning purposes:
`Kaggle CSV → dlt → MongoDB olist_landing → dlt → BigQuery olist_raw`. Unlike the shared
BigQuery project ([docs/gcp_setup.md](gcp_setup.md)), **each team member creates their own
personal MongoDB Atlas cluster** — there is no shared cluster and no shared database user.
It's just a raw landing zone that gets fully rebuilt from the same static Kaggle CSVs every
run, so there is nothing to keep in sync between people's clusters; running the pipeline from
five different personal MongoDB instances produces the same `olist_raw` tables in the one
shared BigQuery project either way.

## One-time setup (every team member does this on their own account)

1. Sign up / log in at mongodb.com
   with your own account (any Google account works).
2. **Build a Database** → **M0 (Free)** shared tier → any provider/region (e.g. AWS
   `ap-southeast-1` Singapore) → Create. This is your own cluster — don't share its login with
   teammates, and don't ask them for theirs.
3. **Database & Network Access** (sidebar, under SECURITY) → **Database Users** tab → **Add New
   Database User** → username e.g. `olist_dev`, autogenerate a password and save it.
4. Same page, **Network Access** tab → **Add IP Address** → **Allow Access from Anywhere**
   (`0.0.0.0/0`) — fine for a personal throwaway cluster.
5. **Database → Clusters** → **Connect** → **Drivers** → **Python** → copy the connection
   string, then substitute in your database user's username/password from step 3.

## Per-developer config

Put your connection string in `config/credentials.env` (gitignored — copy the template from
`config/credentials.env.example` if you haven't already):

```
MONGODB_CONNECTION_URL=mongodb+srv://<your_user>:<your_password>@<your_cluster>.mongodb.net/?appName=Cluster0
```

Then run `bash scripts/setup_local_env.sh` — it generates `ingestion/.dlt/secrets.toml` from
this value (both the `destination.mongodb` block used by `csv_to_mongo_pipeline.py` for
writing, and the `sources.mongodb` block used by `mongo_to_bigquery_pipeline.py` for reading
back out — same cluster, split into two blocks only because that's how dlt scopes destination
vs. source credentials). Don't hand-edit `secrets.toml` directly; edit `credentials.env` and
re-run the script.

## CI

CI (`.github/workflows/ci.yml`) needs one fixed connection string to run non-interactively —
use whichever team member owns the scheduled/CI run's personal cluster, added as the GitHub
Actions secret `MONGODB_CONNECTION_URL`. Never commit a real Atlas password anywhere in the repo.
